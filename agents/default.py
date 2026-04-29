class Agent:
    name = "default"

    def build_prompt(self, code):
        # L'agent ne modifie pas le code
        return code
