import json
from copy import deepcopy
from getpass import getpass

from ..context import Context
from ..executor import Executor
from ..op_template import PythonScriptOPTemplate, ShellOPTemplate
from ..utils import randstr
from ..workflow import Workflow

succ_code = [0, "0000"]


class BohriumExecutor(Executor):
    """
    Bohrium executor

    Args:
        executor: executor
        extra: extra arguments, will override extra defined in global context
    """

    def __init__(
            self,
            executor: str = None,
            extra: dict = None,
    ) -> None:
        self.executor = executor
        self.extra = extra

    def render(self, template):
        assert "workflow.dp.tech/executor" in template.annotations, \
            "bohrium context not detected, bohrium executor will "\
            "not take effect"
        new_template = deepcopy(template)
        new_template.name += "-" + randstr()
        if self.executor is not None:
            new_template.annotations["workflow.dp.tech/executor"] = \
                self.executor
        if self.extra is not None:
            new_template.annotations["task.dp.tech/extra"] = json.dumps(
                self.extra) if isinstance(self.extra, dict) else self.extra
        if self.executor == "bohrium_v2" and template.annotations[
                "workflow.dp.tech/executor"] != "bohrium_v2":
            new_template.script = new_template.script.replace(
                "/tmp", "$(pwd)/tmp")
            if isinstance(template, ShellOPTemplate):
                new_template.script = "mkdir -p tmp\n" + new_template.script
            if isinstance(template, PythonScriptOPTemplate):
                new_template.script = "import os\nos.makedirs('tmp', "\
                    "exist_ok=True)\n" + new_template.script
        return new_template


class BohriumContext(Context):
    """
    Bohrium context

    Args:
        username: user name for Bohrium
        password: password for Bohrium
        login_url: login url for Bohrium
        executor: executor
        extra: extra arguments
        authorization: JWT token
    """

    def __init__(
            self,
            username: str = None,
            password: str = None,
            login_url: str = "https://bohrium.dp.tech/account/login",
            executor: str = None,
            extra: dict = None,
            authorization: str = None,
    ) -> None:
        self.login_url = login_url
        self.username = username
        self.password = password
        self.executor = executor
        self.extra = extra
        self.authorization = authorization
        self.login()

    def login(self):
        if self.authorization is None:
            if self.username is None:
                self.username = input("Bohrium username: ")
            if self.password is None:
                self.password = getpass("Bohrium password: ")
            data = {
                "username": self.username,
                "password": self.password,
            }
            import requests
            rsp = requests.post(self.login_url, headers={
                                "Content-type": "application/json"}, json=data)
            res = json.loads(rsp.text)
            if res["code"] not in succ_code:
                if "error" in res:
                    raise RuntimeError("Login failed: %s" %
                                       res["error"]["msg"])
                elif "message" in res:
                    raise RuntimeError("Login failed: %s" % res["message"])
                else:
                    raise RuntimeError("Login failed")
            self.authorization = res["data"]["token"]

    def render(self, template):
        if isinstance(template, Workflow):
            template.annotations["workflow.dp.tech/executor"] = self.executor
            template.annotations["task.dp.tech/extra"] = json.dumps(
                self.extra) if isinstance(self.extra, dict) else self.extra
            template.annotations["workflow.dp.tech/authorization"] = \
                self.authorization
            return template

        if isinstance(template, (ShellOPTemplate, PythonScriptOPTemplate)):
            new_template = deepcopy(template)
            new_template.name += "-" + randstr()
            new_template.annotations["workflow.dp.tech/executor"] = \
                self.executor
            if self.executor == "bohrium_v2":
                new_template.script = new_template.script.replace(
                    "/tmp", "$(pwd)/tmp")
                if isinstance(template, ShellOPTemplate):
                    new_template.script = "mkdir -p tmp\n" + \
                        new_template.script
                if isinstance(template, PythonScriptOPTemplate):
                    new_template.script = "import os\nos.makedirs('tmp', "\
                        "exist_ok=True)\n" + new_template.script
            return new_template

        return template
