import os
from program import program
from prompter import prompter
import utils
import time
import pandas as pd
import logging
import traceback

class verifier:
    def __init__(self,timeout):
        self.timeout = timeout
        
    def process_yaml(self, file):
        self.setup_logging(file)
        self.log_message("info", f"Processing file {file}")
        
        final_result = "unknown"
        start_time = time.time()
        try:
            prog = program(file)
            source_code = prog.code
            prog.get_data_scale_optima_code()
            data_scale_optima_code = prog.code
            data_scale_optima_LLM = prompter()
            data_scale_optima_answer, data_scale_optima_variables_with_assign = data_scale_optima_LLM.data_scale_optima_completion(data_scale_optima_code)

            if data_scale_optima_answer == "true":                
                if not isinstance(data_scale_optima_variables_with_assign, dict):
                    data_scale_optima_variables_with_assign = dict(data_scale_optima_variables_with_assign)
                
                code_after_optima = prog.data_scale_optima(data_scale_optima_variables_with_assign)
            
                cbmc_result = self.run_cbmc(code_after_optima, timeout=self.timeout - time.time() + start_time)
                final_result = cbmc_result

            elif data_scale_optima_answer == "false":
                scanf_LLM = prompter()
                test_code = prog.code2test(scanf_LLM)
                if test_code is None:
                    final_result = "unknown"
                else:
                    with open('test_program.c', 'w') as file:
                        file.write(test_code)
                    utils.run_command(['gcc', 'test_program.c', '-o', 'test_program'])
                    if not prog.random_var_exist:
                        if os.path.exists("test_program"):
                            defect_analysis_run_command_result = utils.run_command(['./test_program'], timeout=10)
                            defect_analysis_result = defect_analysis_run_command_result['stdout']
                        else:
                            defect_analysis_result = "unknown"
                    else:
                        defect_analysis_LLM = prompter()
                        defect_exist, defect_analysis_process = defect_analysis_LLM.defect_analysis(source_code)
                        if defect_exist == "true":
                            defect_analysis_result = self.run_cbmc(source_code,timeout = self.timeout - time.time() + start_time)
                        else:
                            conterexample_generator = prompter()
                            with open("./prompt_templates/conterexample_sys.txt", 'r') as file:
                                conterexample_sys_content = file.read()
                            with open("./prompt_templates/conterexample_user.txt", 'r') as file:
                                conterexample_user_content = file.read()
                            with open("./prompt_templates/conterexample_repair.txt", 'r') as file:
                                conterexample_repair_content = file.read()
                            with open("./prompt_templates/conterexample_assume_false.txt", 'r') as file:
                                conterexample_assume_false_content = file.read()
                            with open("./prompt_templates/timeout.txt", 'r') as file:
                                timeout_content = file.read()
                            conterexample_messages =  [
                                {"role": "system", "content": conterexample_sys_content},
                                {"role": "user", "content": "Analyzed code:\n" + test_code + "\n\n" + "Previous analysis:\n" + defect_analysis_process + "\n\n"+ conterexample_user_content},
                            ]
                            iterations = 0
                            while iterations < 5:
                                iterations += 1               
                                conterexample_code, conterexample_reply_messages = conterexample_generator.generate_couterexample_completion(conterexample_messages)
                                with open('input_program.c', 'w') as file:
                                    file.write(conterexample_code)
                                utils.run_command(['gcc', 'input_program.c', '-o', 'input_program'])
                                input_anwser = utils.run_command(['./input_program'])
                                defect_analysis_input = input_anwser['stdout']
                                conterexample_messages.append({"role": "assistant", "content": conterexample_reply_messages})
                                defect_analysis_run_command_result = utils.run_command(['./test_program'], input=defect_analysis_input,timeout=10)
                                defect_analysis_result = defect_analysis_run_command_result["stdout"]
                                os.remove("input_program")
                                os.remove("input_program.c")
                                if defect_analysis_result == "true":
                                    defect_analysis_result = "after test no defect found"
                                    conterexample_messages.append({"role": "user", "content": conterexample_repair_content})
                                elif defect_analysis_result == "false":
                                    break
                                elif defect_analysis_result == "assume false":
                                    defect_analysis_result = "after test no defect found"
                                    conterexample_messages.append({"role": "user", "content": conterexample_assume_false_content})
                                elif defect_analysis_result == "timeout":
                                    defect_analysis_result = "after test no defect found"
                                    conterexample_messages.append({"role": "user", "content": timeout_content})
                            if iterations == 5:
                                defect_analysis_result = self.run_cbmc(source_code,timeout = self.timeout - time.time() + start_time)
                        
                if os.path.exists("test_program"):
                    os.remove("test_program")
                if os.path.exists("test_program.c"):
                    os.remove("test_program.c")
                final_result = defect_analysis_result
            else:
                self.log_message("info", f"unknown optimization result")
                final_result = self.run_cbmc(source_code,timeout = self.timeout - time.time() + start_time)
                    
        except Exception as e:
            final_result = "unknown"
            error_details = traceback.format_exc()
            print(error_details)
            self.log_message("error", f"Error occurred: {e}")
        
        total_time = round(time.time() - start_time, 2)   
        self.log_message("info", f"Verification result: {final_result}, time taken: {total_time} seconds")
        
    def run_cbmc(self, code, timeout):
        with open("tmp.c", 'w') as out_file:
            out_file.write(code)
        utils.clang_format('tmp.c')
        
        command = [
            "/usr/bin/time",
            "-v",
            "cbmc",
            "--no-standard-checks",
            "--no-built-in-assertions",
            "--verbosity",
            "4",
            "tmp.c"
        ]
        result = "unknown"
        p = utils.run_command(command, timeout = timeout)
        if not p["timed_out"]:
            output = p["stdout"]
            stderr = p["stderr"]
            if "VERIFICATION SUCCESSFUL" in output:
                result = "true"    
            elif "VERIFICATION FAILED" in output:
                result = "false"
        else:
            result = "timeout"
        os.remove("tmp.c")
        return result

    def setup_logging(self, file):
        log_file_path = os.path.join(f"{file}.log")
        logging.basicConfig(
            filename=log_file_path,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        
    def log_message(self, level, message):
        if level == "info":
            logging.info(message)
        elif level == "error":
            logging.error(message)
        elif level == "debug":
            logging.debug(message)
        print("\n", message)
    