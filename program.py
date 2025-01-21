import re
import utils
import os

class program:
    def __init__(self, yml_file):
        self.get_input_files_content(yml_file)
        self.clang_format()
        self.remove_empty_lines()
   
    
    def get_data_scale_optima_code(self):
        self.remove_malloc()
        
    def remove_malloc(self):
        pattern = r'^\s*void \*malloc\s*\('
        lines = self.code.split('\n')
        filtered_lines = [line for line in lines if not re.match(pattern, line)]
        self.code = '\n'.join(filtered_lines)

    def remove_empty_lines(self):
        lines = self.code.split("\n")
        new_lines = []
        for line in lines:
            if line == "":
                continue
            else:
                new_lines.append(line)
        new_code = "\n".join(new_lines) 
        
        self.code = new_code

    def clang_format(self):
        with open("tmp.c", 'w') as out_file:
            out_file.write(self.code)
        utils.clang_format('tmp.c')
        with open("tmp.c", 'r') as file:
            new_code = file.read()
        os.remove("tmp.c")
        
        self.code = new_code

    def data_scale_optima(self, downsize_variables):
        code_after_optima = self.code
        for var, val in downsize_variables.items():

            pattern_define = r'#define\s+' + re.escape(var) + r'\s+(.+)'
            pattern_assign = r'(\b{var}\b)\s*=\s*(.+?);'.format(var=re.escape(var))
            if re.search(pattern_define, code_after_optima, re.MULTILINE):
                replacement_define = f'#define {var} {val}'
                code_after_optima = re.sub(pattern_define, replacement_define, code_after_optima)
            elif re.search(pattern_assign, code_after_optima):
                replacement_assign = f'{var} = {val};'
                code_after_optima = re.sub(pattern_assign, replacement_assign, code_after_optima)

        return code_after_optima

    def get_input_files_content(self, file):
        with open(file, 'r') as file:
            self.code = file.read()
            
    def code2test(self, scanf_LLM):
        self.remove_externs()
        self.remove_function("void assume_abort_if_not")
        self.remove_function("void reach_error")
        self.code = self.code.replace("assume_abort_if_not", "assume")
        self.find_verifier_nondet()
        self.add_reach_error()
        self.process_code()
        
        if self.random_var_exist:
            for var_inline in self.random_vars:
                value_of_var = scanf_LLM.rand2scanf(var_inline)
                if value_of_var is None:
                    return None
                self.code = self.code.replace(var_inline.strip(), value_of_var)
        self.clang_format()
        self.remove_empty_lines()
        return self.code
        
    def remove_function(self,func_name):
        function_index = self.code.find(func_name)
        if function_index == -1:
            return None
        open_brackets = 0
        close_brackets = 0

        for i in range(function_index, len(self.code)):
            if self.code[i] == '{':
                open_brackets += 1
            elif self.code[i] == '}':
                close_brackets += 1
                if open_brackets == close_brackets:
                    break
        self.code = self.code[: function_index] + self.code[i + 1: ]
    
    def remove_externs(self):
        pattern = r'\bextern\s+.*?;'
        functions = re.findall(pattern, self.code, re.MULTILINE | re.DOTALL)
        for function in functions:
            self.code = self.code.replace(function, "")
        self.code = self.code.strip()
        lines = self.code.split("\n")
        new_lines = []
        for line in lines:
            if line.strip()[:13] == "__extension__":
                new_lines.append(line[13:])
            else:
                new_lines.append(line)
        self.code = "\n".join(new_lines)

    def find_verifier_nondet(self):
        tokens = self.get_tokens_with_verifier_nondet(self.code)
        self.random_var_exist = bool(tokens)
        self.random_vars = []  

        lines = self.code.split('\n')
        for i, line in enumerate(lines):
            for token in tokens:
                pattern = re.compile(r'\b' + re.escape(token) + r'\(\)')
                if pattern.search(line):
                    extern_pattern = re.compile(r'\bextern\s+.*?;')
                    if extern_pattern.search(line):
                        continue
                    #replacement = self.nondet_type(token.split("__VERIFIER_nondet_")[1]) + "rand()"
                    #random_var = line.replace(token + "()", replacement).strip()
                    self.random_vars.append(line)
                    #lines[i] = random_var
                    break

    def get_tokens_with_verifier_nondet(self, input_string):
        pattern = r'\b__VERIFIER_nondet_\w+\b'
        tokens = set(re.findall(pattern, input_string))
        return tokens
    
    def nondet_type(self, type_str):
        if type_str == "uchar":
            return "(unsigned char)"
        elif type_str == "char":
            return "(signed char)"
        elif type_str == "uint":
            return "(unsigned int)"
        else:
            return f"({type_str})" 
        
    def add_reach_error(self):
        reach_error_code = 'void reach_error() {\n  printf("false");\n  exit(0);\n}\n\n'
        self.code = reach_error_code + self.code
                
    def process_code(self):
        assume_pattern = re.compile(r'assume\((.*?)\);', re.DOTALL)
        def replace_assume(match):
            expr = match.group(1)
            return f'if(!({expr})) {{\n    printf("assume false");\n exit(0);\n}}'
        self.code = assume_pattern.sub(replace_assume, self.code)

        lines = self.code.split('\n')
        main_end_index = -1
        return_index = -1
        
        for i, line in enumerate(lines):
            if 'int main' in line:
                main_end_index = i
                break
        left_num = 1
        right_num = 0
        if main_end_index != -1:
            for i in range(main_end_index + 1, len(lines)):
                if '{' in lines[i]:
                    left_num += 1
                elif '}' in lines[i]:
                    right_num += 1
                    if left_num == right_num:
                       main_end_index = i
                       break
                elif 'return' in lines[i]:
                    return_index = i

            if return_index != -1:
                indentation = re.match(r'^\s*', lines[return_index]).group()
                lines.insert(return_index, f'{indentation}printf("true");\n')
            else:
                indentation = re.match(r'^\s*', lines[main_end_index]).group()
                lines.insert(main_end_index, f'{indentation}printf("true");\n')
        
        self.code = '\n'.join(lines)
        
        self.clang_format()