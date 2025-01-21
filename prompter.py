from openai import OpenAI
import json
import re
import os

class prompter:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY")
        self.client = OpenAI(
            api_key = self.api_key,
            base_url = "https://api.deepseek.com"
        )
    
    def data_scale_optima_completion(self,code):
        with open("./prompt_templates/DataScaleOptima_sys.txt", 'r') as file:
            sys_content = file.read()
        
        with open("./prompt_templates/DataScaleAnalysis_user.txt", 'r') as file:
            data_scale_analysis_content = file.read()
        messages=[
            {"role": "system", "content": sys_content},
            {"role": "user", "content": data_scale_analysis_content + '\n' + code}
        ]

        data_scale_analysis_completion = self.generate_completion(messages=messages,response_format={"type": "text"})
        messages.append({"role": "assistant", "content": data_scale_analysis_completion})
        
        with open("./prompt_templates/DataScaleOptima_get_ans.txt", 'r') as file:
            get_ans_content = file.read()
        messages.append({"role": "user", "content": get_ans_content})
        
        get_ans_completion = self.generate_completion(messages=messages,response_format={"type": "json_object"})
        messages.append({"role": "assistant", "content": get_ans_completion})
        json_get_ans_completion = json.loads(get_ans_completion, strict=False)
        result = str(json_get_ans_completion['result']).lower()
        if result == "false":
            return result, None
        else:            
            with open("./prompt_templates/DataScaleOptima_get_var.txt", 'r') as file:
                get_var_content = file.read()
            messages.append({"role": "user", "content": get_var_content})    
            
            get_var_completion = self.generate_completion(messages=messages,response_format={"type": "json_object"})
            messages.append({"role": "assistant", "content": get_var_completion})
            json_get_var_completion = json.loads(get_var_completion, strict=False)
            data_scale_variables_with_assign = json_get_var_completion['variables']
            
        return result, data_scale_variables_with_assign
    
    def rand2scanf(self,var_inline):
        declaration, assignment = self.parse_var_inline(var_inline)
        if assignment is None:
            return None, None
        
        with open("./prompt_templates/rand2scanf_sys.txt", 'r') as file:
            sys_content = file.read()
        with open("./prompt_templates/rand2scanf_user.txt", 'r') as file:
            rand2scanf_content = file.read()
        messages=[
            {"role": "system", "content": sys_content},
            {"role": "user", "content": assignment + '\n' + rand2scanf_content}
        ]
        rand2scanf_completion = self.generate_completion(messages=messages,response_format={"type": "json_object"})
        json_rand2scanf_completion = json.loads(rand2scanf_completion, strict=False)
        rand2scanf_code = json_rand2scanf_completion['code']
        messages.append({"role": "assistant", "content": rand2scanf_completion})
        if declaration:
            result = declaration + '\n' + rand2scanf_code
        else:
            result = rand2scanf_code
        return result
    
    def parse_var_inline(self,var_inline):
        pattern = r'^(?:(\w+)\s+)?(\w+)\s*=\s*(.+);$'
        match = re.match(pattern, var_inline.strip())
        
        if match:
            declaration_type = match.group(1)
            variable_name = match.group(2)
            assignment_expression = match.group(3)
            
            declaration = f"{declaration_type} {variable_name};" if declaration_type else None
            assignment = f"{variable_name} = {assignment_expression};"
            
            return declaration, assignment
        else:
            return None, None
    
    def defect_analysis(self,code):
        with open("./prompt_templates/DefectAnalysis_sys.txt", 'r') as file:
            sys_content = file.read()
        with open("./prompt_templates/DefectAnalysis_user.txt", 'r') as file:
            defect_analysis_content = file.read()
        messages=[
            {"role": "system", "content": sys_content},
            {"role": "user", "content": code + '\n' + defect_analysis_content}
        ]        
        defect_analysis_completion = self.generate_completion(messages=messages,response_format={"type": "text"})
        messages.append({"role": "assistant", "content": defect_analysis_completion})
        
        with open("./prompt_templates/DefectAnalysis_get_ans.txt", 'r') as file:
            get_ans_content = file.read()
        messages.append({"role": "user", "content": get_ans_content})
        get_ans_completion = self.generate_completion(messages=messages,response_format={"type": "text"})
        messages.append({"role": "assistant", "content": get_ans_completion})
        defect_exist = get_ans_completion.lower()
        
        
        return defect_exist, defect_analysis_completion
    
    def generate_couterexample_completion(self, messages):
        counterexample_completion = self.generate_completion(messages,response_format={"type": "json_object"})
        json_counterexample_completion = json.loads(counterexample_completion, strict=False)
        conterexample_code = json_counterexample_completion['output program']
        
        return conterexample_code, counterexample_completion
    
    def generate_completion(self,messages,response_format):
        completion = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=1,
            response_format=response_format                    
        )        
        return completion.choices[0].message.content