import json
import time
from turtle import reset

import openai
import streamlit as st
import yfinance as yf

ASSISTANT_ID = "asst_mRHCpOtu5JW6VYPOyyT0vciq"


def get_stock_price(symbol):
    stock = yf.Ticker(symbol)
    price = stock.info["currentPrice"]
    return price


def get_latest_company_news(symbol):
    stock = yf.Ticker(symbol)
    news = stock.news
    news_list = []
    num = 1
    for item in news[:3]:
        news_list.append(
            f"{num}: title : {item['title']}, publisher: {item['publisher']}, link : {item['link']}"
        )
        num += 1
    return news_list


def requires_actions(client, run):
    tools_to_call = run.required_action.submit_tool_outputs.tool_calls
    tools_output_array = []
    for each_tool in tools_to_call:
        tool_call_id = each_tool.id
        function_name = each_tool.function.name
        function_args = each_tool.function.arguments
        function_args = json.loads(each_tool.function.arguments)

        if function_name == "get_stock_price":
            output = get_stock_price(function_args["symbol"])
        if function_name == "get_latest_company_news":
            output = get_latest_company_news(function_args["symbol"])

        print("Function Name: ", function_name)
        print("Function Args: ", function_args)
        print("Output: ", output)
        tools_output_array.append({
            "tool_call_id": tool_call_id,
            "output": json.dumps(output),
        })

    run = client.beta.threads.runs.submit_tool_outputs(
        thread_id=st.session_state.Thread.id,
        run_id=run.id,
        tool_outputs=tools_output_array,
    )

    while run.status not in ["completed", "failed", "requires_action"]:
        run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.Thread.id,
            run_id=run.id,
        )
        time.sleep(1)
    return run


def get_response(client, run):
    if run.status == "queued":
        while run.status not in ["completed", "failed", "requires_action"]:
            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.Thread.id,
                run_id=run.id,
            )
            time.sleep(2)
        response = get_response(client, run)
    elif run.status == "requires_action":
        run = requires_actions(client, run)
        response = get_response(client, run)
    elif run.status == "completed":
        messages = client.beta.threads.messages.list(
            thread_id=st.session_state.Thread.id
        )
        response = messages.data[0].content[0].text.value
    else:
        response = "문제가 발생했습니다. 다시 질문해주세요"

    return response


def main():
    st.set_page_config(page_title="주가 정보 AI 챗봇", page_icon="📈", layout="wide")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "Thread" not in st.session_state:
        st.session_state.Thread = None

    st.header("주가 정보 AI 챗봇")
    st.markdown("---")

    is_submit = False

    with st.sidebar:
        st.write("대화 초기화 버튼")
        reset_button = st.button("Reset")
        if reset_button:
            st.session_state.messages = []
            st.session_state.Thread = None

        with st.form(key="API Keys"):
            openai_key = st.text_input(
                label="OpenAI API Key",
                key="openai_api_key",
                type="password",
                help="OpenAI API 키는 https://platform.openai.com/account/api-keys 에서 발급 가능합니다.",
            )

            btn = st.form_submit_button(label="Submit")

    if len(openai_key) < 10:
        return
    client = openai.OpenAI(api_key=openai_key)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            st.markdown(message["content"])

    assistant = client.beta.assistants.retrieve(ASSISTANT_ID)

    if st.session_state.Thread is None:
        st.session_state.Thread = client.beta.threads.create()

    if prompt := st.chat_input("조회를 원하는 종목을 말씀하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        message = client.beta.threads.messages.create(
            thread_id=st.session_state.Thread.id,
            role="user",
            content=prompt,
        )
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Thinking..."):
            run = client.beta.threads.runs.create(
                thread_id=st.session_state.Thread.id,
                assistant_id=assistant.id,
            )
            response = get_response(client, run)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
