

import os
from threading import Thread, Event
import time
from typing import Any, Dict, List, Optional
import autogen
from autogen import ChatResult
import instructor
import sys
from openai import OpenAI

# append parent directory to PATH to import own modules
sys.path.append(os.path.dirname(os.path.abspath(os.getcwd())))

from config_for_clarify import (
    ANALYST_SYSTEM_MESSAGE,
    CODER_SYSTEM_MESSAGE,
    EXECUTOR_SYSTEM_MESSAGE,
    start_message
)
from browser import open_browser_session
from model.chat import Chat

class Test:

    def __init__(
        self,
        base_model: str | None = None,
        execution_config: Dict[str, Any] | None = None,
        summary_method: str | None = None,
        max_round: int = 50
    ) -> None:

        self.base_model: str = base_model or "gpt-4.1-mini"
        self.execution_config: Dict[str, Any] | None = execution_config
        if not execution_config:
            self.execution_config: Dict[str, Any] = {
                "last_n_messages": 3,
                "work_dir": "web",
                "use_docker": False,
            }
        self.summary_method: str = summary_method or "reflection_with_llm"
        self.max_round: int = max_round
        self.exceptions_per_crawl: int = 0

        ### OpenAI instance ###
        self.oai_client: OpenAI = instructor.patch(OpenAI(), mode=instructor.Mode.JSON)

        ### Browser Thread Setup ###
        self.trigger_crawl_start_event: Event = Event()
        self.trigger_thread_stop_event: Event = Event()
        self.start_url: str | None = None
        self.browser_thread: Thread | None = None

        ### AutoGen Agent configuration ###
        self._llm_config_list: List[Dict[str, str]] = [
            {
                "model": self.base_model,
                "base_url": "https://api.openai.com/v1",
                "api_key": os.environ.get("OPENAI_API_KEY")
            }
        ]
        self.autogen_llm_config: Dict[str, Any] = {
            "timeout": 600,
            "cache_seed": None,
            "config_list": self._llm_config_list,
            "temperature": 0.2,
        }
        self._initialize_agents()
        self.groupchat = autogen.GroupChat(
            agents=[self.coder, self.executor, self.analyst],
            messages=[],
            max_round=self.max_round,
            speaker_selection_method=self.state_transition,
        )
        self.manager = autogen.GroupChatManager(
            groupchat=self.groupchat,
            llm_config=self.autogen_llm_config
        )


    def _initialize_agents(self) -> None:
        """
        """
        self.coder = autogen.ConversableAgent(
            system_message=CODER_SYSTEM_MESSAGE,
            name="Coder",
            llm_config=self.autogen_llm_config,
        )
        self.executor = autogen.UserProxyAgent(
            name="Executor",
            human_input_mode="NEVER",
            code_execution_config=self.execution_config,
            llm_config=self.autogen_llm_config,
            system_message=EXECUTOR_SYSTEM_MESSAGE
        )
        self.analyst = autogen.ConversableAgent(
            name="Analyst",
            llm_config=self.autogen_llm_config,
            human_input_mode="NEVER"
        )


    def _reset_agents(self) -> None:
        self.coder.reset()
        self.executor.reset()
        self.analyst.reset()
        self.groupchat.reset()
        self.manager.reset()


    def state_transition(self, last_speaker, groupchat) -> autogen.ConversableAgent | None:
        messages = groupchat.messages

        if last_speaker is self.manager:
            return self.analyst
        elif last_speaker is self.coder:
            return self.executor
        elif last_speaker is self.executor:
            return self.analyst
        elif last_speaker is self.analyst:
            if "IsPass: 0" in messages[-1]["content"] or "IsPass: petclinic" in messages[-1]["content"]:
                return None
            return self.coder
        else: return None


    def start_browser(self, start_url) -> bool:
        """Resets all event triggers and starts a new browser instance."""
        # clear events
        if self.browser_thread is None:
            self.trigger_thread_stop_event.clear()
            self.trigger_crawl_start_event.clear()
            self.browser_thread = Thread(
                target=open_browser_session,
                args=(start_url, self.trigger_crawl_start_event, self.trigger_thread_stop_event,)
            )
            self.browser_thread.start()
            return True
        return False


    def stop_browser(self, auto_stop: bool) -> None:
        """Clears all event triggers and stops all browser instances."""

        # Run is finished, thread and browser can be closed by setting this event
        if auto_stop is True:
            self.trigger_thread_stop_event.set()
            self.browser_thread.join()
            self.browser_thread = None
            self.trigger_thread_stop_event.clear()
            self.trigger_crawl_start_event.clear()


    def get_nr_code_errors(chat_history):
        errors = 0
        for message in chat_history:
            if 'name' in message and  message['name'] == "Executor" and "exitcode: petclinic" in message['content']:
                errors += 1
        return errors


    def get_nr_generated_scripts(chat_history):
        scripts = 0
        for message in chat_history:
            if 'name' in message and  message['name'] == "Coder" and "```python" in message['content']:
                scripts += 1
        return scripts


    def run(
        self,
        prompt: str,
        start_url: str | None = None,
        html_elements: str | None = None,
        auto_stop: bool = True
    ) -> Optional[Chat]:
        """
        """
        self.exceptions_per_crawl = 0
        is_browser_started: bool = self.start_browser(start_url)
        # if a browser session is running, then set the start url to None
        if not is_browser_started:
            start_url = None
        # self.coordinator.update_system_message(COORDINATOR_SYSTEM_MESSAGE(prompt, start_url))
        self.analyst.update_system_message(ANALYST_SYSTEM_MESSAGE(prompt))

        # Wait for the page content to be initialized and loaded before starting the crawling
        is_page_loaded: bool = self.trigger_crawl_start_event.wait(timeout=30)
        if not is_page_loaded:
            print("ERROR: Page loading too long, aborting...")
            return None

        # from playwright.sync_api import sync_playwright
        #
        # with sync_playwright() as playwright:
        #     # Access existing browser session
        #     browser = playwright.chromium.connect_over_cdp("http://localhost:9222/")
        #     default_context = browser.contexts[0]
        #     # this page object already points to your current url
        #     page = default_context.pages[0]
        #
        #     page.fill("#username", "abc")
        #     page.fill("#password", "123456@Mm")
        #     page.click('button:has-text("Sign In")')
        #
        #     page.wait_for_selector("a[href='/transactions/new']", state="visible")
        #     page.click("a[href='/transactions/new']")
        #
        #     # Print the current url's html code
        #     print(page.content())
        #     # Print the current url itself
        #     print(page.url)

        # from playwright.sync_api import sync_playwright
        #
        # with sync_playwright() as playwright:
        #     # Access existing browser session
        #     browser = playwright.chromium.connect_over_cdp("http://localhost:9222/")
        #     default_context = browser.contexts[0]
        #     # this page object already points to your current url
        #     page = default_context.pages[0]
        #
        #     page.fill("#username", "abcde")
        #     page.fill("#password", "12345")
        #     page.click("input[type='submit']")
        #
        #     # 点击New Post链接
        #     page.get_by_role("link", name="New Post", exact=True).click()
        #     # 或者使用CSS选择器：page.locator("a[href='/newPost']").click()
        #
        #     # 等待新页面加载完成（可选但推荐）
        #     page.wait_for_url("**/newPost")
        #
        #     # Print the current url's html code
        #     print(page.content())
        #     # Print the current url itself
        #     print(page.url)

        start_time: float = time.time()
        # TOKEN CONSUMPTION STARTS HERE
        chat_result: ChatResult = self.analyst.initiate_chat(
            self.manager,
            message=start_message(prompt, start_url, html_elements),
            summary_method=self.summary_method,
        )
        end_time: float = time.time()
        duration: float = end_time - start_time

        self.stop_browser(auto_stop)

        if auto_stop:
            # to completely avoid any information or metric flow between runs
            self._reset_agents()


        result: Chat = Chat(
            history=chat_result.chat_history,
            duration=duration,
            nr_tokens=sum(
            model_usage.get("total_tokens", 0)
                for model_usage in chat_result.cost.get(
                    "usage_excluding_cached_inference", {}
                ).values()
                if isinstance(model_usage, dict)
            ),
            interactions=len(chat_result.chat_history),
            nr_generated_scripts=Test.get_nr_generated_scripts(chat_result.chat_history),
            nr_code_errors=Test.get_nr_code_errors(chat_result.chat_history),
            summary=chat_result.summary,
            gherkin=True if("GIVEN" in prompt or "WHEN" in prompt or "THEN" in prompt) else False
        )

        return result


if __name__ == "__main__":
    example_input: str = """Feature: Add owner
Given this is the current URL: "http://localhost:8080/owners/new"
When I add a person with first name "John*" and last name "Smith" with address "412 Main Street", city "NewYork", and telephone "6095916230" as a new pet owner
Then "John* Smith" is not an owner """
    start_url: str = "http://localhost:8080/owners/new"
    html_elements: str = """<html><head>

  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <link rel="shortcut icon" type="image/x-icon" href="/resources/images/favicon.png">

  <title>PetClinic :: a Spring Framework demonstration</title>

  <!--[if lt IE 9]>
    <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>
    <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
    <![endif]-->

  <link href="/webjars/font-awesome/4.7.0/css/font-awesome.min.css" rel="stylesheet">
  <link rel="stylesheet" href="/resources/css/petclinic.css">

</head>

<body>

  <nav class="navbar navbar-expand-lg navbar-dark" role="navigation">
    <div class="container-fluid">
      <a class="navbar-brand" href="/"><span></span></a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#main-navbar">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="main-navbar" style="">

        

        <ul class="nav navbar-nav me-auto">

          <li class="nav-item">
            <a class="nav-link" href="/" title="home page">
              <span class="fa fa-home"></span>
              <span>Home</span>
            </a>
          </li>

          <li class="nav-item">
            <a class="nav-link active" href="/owners/find" title="find owners">
              <span class="fa fa-search"></span>
              <span>Find owners</span>
            </a>
          </li>

          <li class="nav-item">
            <a class="nav-link" href="/vets.html" title="veterinarians">
              <span class="fa fa-th-list"></span>
              <span>Veterinarians</span>
            </a>
          </li>

          <li class="nav-item">
            <a class="nav-link" href="/oups" title="trigger a RuntimeException to see how it is handled">
              <span class="fa fa-exclamation-triangle"></span>
              <span>Error</span>
            </a>
          </li>

        </ul>
      </div>
    </div>
  </nav>
  <div class="container-fluid">
    <div class="container xd-container">

      

  <h2>Owner</h2>
  <form class="form-horizontal" id="add-owner-form" method="post">
    <div class="form-group has-feedback">
      
      <div class="form-group">
        <label class="col-sm-2 control-label">First Name</label>
        <div class="col-sm-10">
            <div>
                <input class="form-control" type="text" id="firstName" name="firstName" value="">
                
            </div>
          <span class="fa fa-ok form-control-feedback" aria-hidden="true"></span>
          
        </div>
      </div>
    
      
      <div class="form-group">
        <label class="col-sm-2 control-label">Last Name</label>
        <div class="col-sm-10">
            <div>
                <input class="form-control" type="text" id="lastName" name="lastName" value="">
                
            </div>
          <span class="fa fa-ok form-control-feedback" aria-hidden="true"></span>
          
        </div>
      </div>
    
      
      <div class="form-group">
        <label class="col-sm-2 control-label">Address</label>
        <div class="col-sm-10">
            <div>
                <input class="form-control" type="text" id="address" name="address" value="">
                
            </div>
          <span class="fa fa-ok form-control-feedback" aria-hidden="true"></span>
          
        </div>
      </div>
    
      
      <div class="form-group">
        <label class="col-sm-2 control-label">City</label>
        <div class="col-sm-10">
            <div>
                <input class="form-control" type="text" id="city" name="city" value="">
                
            </div>
          <span class="fa fa-ok form-control-feedback" aria-hidden="true"></span>
          
        </div>
      </div>
    
      
      <div class="form-group">
        <label class="col-sm-2 control-label">Telephone</label>
        <div class="col-sm-10">
            <div>
                <input class="form-control" type="text" id="telephone" name="telephone" value="">
                
            </div>
          <span class="fa fa-ok form-control-feedback" aria-hidden="true"></span>
          
        </div>
      </div>
    
    </div>
    <div class="form-group">
      <div class="col-sm-offset-2 col-sm-10">
        <button class="btn btn-primary" type="submit">Add Owner</button>
      </div>
    </div>
  </form>


      <br>
      <br>
      <div class="container">
        <div class="row">
          <div class="col-12 text-center">
            <img src="/resources/images/spring-logo.svg" alt="VMware Tanzu Logo" class="logo">
          </div>
        </div>
      </div>
    </div>
  </div>

  <script src="/webjars/bootstrap/5.3.3/dist/js/bootstrap.bundle.min.js"></script>




</body></html>"""

    crawler: Test = Test()
    result: Chat = crawler.run(example_input, start_url, html_elements)
    statistics = f"Statistics:\n  Interactions: {result.interactions}\n  Number of tokens: {result.nr_tokens}\n  Duration: {result.duration:.2f} seconds\n  Generated code scripts: {result.nr_generated_scripts}\n  Code errors: {result.nr_code_errors}\n  Summary: " + result.summary + "\n"
    print(statistics)

    # +++ 新增的保存功能 +++
    output_dir = r"C:\Users\DELL\Desktop\WebMAC\Experiment_Runs\RQ1_2\DialogicMT\petclinic"
    output_file = os.path.join(output_dir, "8_test")

    # 确保目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 写入结果
    with open(output_file, "w", encoding='utf-8') as f:
        f.write(statistics)
        # 如果需要保存完整对话历史，可以取消下面注释
        f.write("\n\nFull Chat History:\n")
        for msg in result.history:
            f.write(f"{msg['name']}: {msg['content']}\n\n")

    print(f"Results saved to {output_file}")