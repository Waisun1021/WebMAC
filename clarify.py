"""
"""

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
    MY_CODER_SYSTEM_MESSAGE,
    MY_EXECUTOR_SYSTEM_MESSAGE,
    MY_CLARIFY_SYSTEM_MESSAGE,
    my_start_message,
    MY_REWRITE_SYSTEM_MESSAGE,
    MY_ANALYST_SYSTEM_MESSAGE,
    MY_COORDINATOR_SYSTEM_MESSAGE
)
from browser import open_browser_session
from model.chat import Chat

class Clarify:

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
            agents=[self.coordinator, self.coder, self.executor, self.analyst, self.clarify, self.rewrite, self.user],
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
            system_message=MY_CODER_SYSTEM_MESSAGE,
            name="Coder",
            llm_config=self.autogen_llm_config,
        )
        self.executor = autogen.UserProxyAgent(
            name="Executor",
            human_input_mode="NEVER",
            code_execution_config=self.execution_config,
            llm_config=self.autogen_llm_config,
            system_message=MY_EXECUTOR_SYSTEM_MESSAGE
        )
        self.analyst = autogen.ConversableAgent(
            name="Analyst",
            system_message=MY_ANALYST_SYSTEM_MESSAGE,
            llm_config=self.autogen_llm_config,
            human_input_mode="NEVER"
        )
        self.coordinator = autogen.ConversableAgent(
            name="Coordinator",
            system_message=MY_COORDINATOR_SYSTEM_MESSAGE,
            llm_config=self.autogen_llm_config,
            human_input_mode="NEVER"
        )
        self.clarify = autogen.ConversableAgent(
            name="Clarify",
            llm_config=self.autogen_llm_config,
            human_input_mode="NEVER"
        )
        self.rewrite = autogen.ConversableAgent(
            name="Rewriter",
            llm_config=self.autogen_llm_config,
            human_input_mode="NEVER"
        )
        self.user = autogen.ConversableAgent(
            "User",
            llm_config=False,  # 人类代理不使用LLM
            human_input_mode="ALWAYS",  # 总是要求人类输入
        )


    def _reset_agents(self) -> None:
        self.coder.reset()
        self.executor.reset()
        self.analyst.reset()
        self.coordinator.reset()
        self.clarify.reset()
        self.rewrite.reset()
        self.user.reset()
        self.groupchat.reset()
        self.manager.reset()


    def state_transition(self, last_speaker, groupchat) -> autogen.ConversableAgent | None:
        messages = groupchat.messages

        if last_speaker is self.manager:
            return self.coordinator
        elif last_speaker is self.coder:
            return self.executor
        elif last_speaker is self.executor:
            return self.analyst
        elif last_speaker is self.analyst:
            if "Exitcode: petclinic" in messages[-1]["content"]:
                self.exceptions_per_crawl += 1
            if self.exceptions_per_crawl == 5:
                return None
            if "IsClarify: petclinic" in messages[-1]["content"]:
                print("Your scenario is very good")
                return self.coordinator
            return self.clarify
        elif last_speaker is self.clarify:
            return self.user
        elif last_speaker is self.user:
            return self.rewrite
        elif last_speaker is self.rewrite:
            return self.coordinator
        elif last_speaker is self.coordinator:
            if "{" in messages[-1]["content"] or "}" in messages[-1]["content"]:
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
        auto_stop: bool = True
    ) -> Optional[Chat]:
        """
        """
        self.exceptions_per_crawl = 0
        is_browser_started: bool = self.start_browser(start_url)
        # if a browser session is running, then set the start url to None
        if not is_browser_started:
            start_url = None
        # self.coordinator.update_system_message(MY_COORDINATOR_SYSTEM_MESSAGE(prompt, start_url))
        self.clarify.update_system_message(MY_CLARIFY_SYSTEM_MESSAGE(prompt))
        self.rewrite.update_system_message(MY_REWRITE_SYSTEM_MESSAGE(prompt))

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
        chat_result: ChatResult = self.coordinator.initiate_chat(
            self.manager,
            message=my_start_message(prompt, start_url),
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
            nr_generated_scripts=Clarify.get_nr_generated_scripts(chat_result.chat_history),
            nr_code_errors=Clarify.get_nr_code_errors(chat_result.chat_history),
            summary=chat_result.summary,
            gherkin=True if("GIVEN" in prompt or "WHEN" in prompt or "THEN" in prompt) else False
        )

        return result


if __name__ == "__main__":
    example_input: str = """Feature: Add owner
Given this is the current URL: "http://localhost:8080/owners/new"
When I add a person with first name "John*" and last name "Smith", address "412 Main Street", and telephone "6095916230"  as a new pet owner
Then "John* Smith" is not an owner """
    start_url: str = "http://localhost:8080/owners/new"

    crawler: Clarify = Clarify()
    result: Chat = crawler.run(example_input, start_url)
    statistics = f"Statistics:\n  Interactions: {result.interactions}\n  Number of tokens: {result.nr_tokens}\n  Duration: {result.duration:.2f} seconds\n  Generated code scripts: {result.nr_generated_scripts}\n  Code errors: {result.nr_code_errors}\n  Summary: " + result.summary + "\n"
    print(statistics)

    # +++ 新增的保存功能 +++
    output_dir = r"C:\Users\DELL\Desktop\WebMAC\Experiment_Runs\RQ1_2\DialogicMT\petclinic"
    output_file = os.path.join(output_dir, "12_clarify")

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