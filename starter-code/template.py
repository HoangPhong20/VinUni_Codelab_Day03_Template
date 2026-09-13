"""
Lab #3: Baseline Chatbot vs ReAct Agent
Học viên hoàn thiện các mục TODO để hoàn thành bài lab.
"""

import json
import re
from tools import TOOL_DEFINITIONS, TOOL_MAP, get_flight_info, get_weather_forecast

SYSTEM_PROMPT = """Bạn là một ReAct Agent thông minh hỗ trợ khách hàng Vingroup.
Bạn chỉ sử dụng các công cụ sau:
{tools}

Quy trình trả lời bắt buộc:
Thought: <Suy nghĩ bước tiếp theo>
Action: {{"name": "<tên tool>", "args": {{<tham số>}}}}
Observation: <Kết quả từ tool>
... (Lặp lại cho tới khi có đủ dữ liệu)
Final Answer: <Câu trả lời hoàn chỉnh cho khách hàng>
"""

class ChatbotBaseline:
    """Baseline LLM Chatbot (Không sử dụng ReAct Loop hay Tools)"""
    def query(self, user_input: str) -> dict:
        return {
            "status": "success",
            "answer": f"[Chatbot Baseline] Trả lời cho: {user_input}",
            "tool_calls": [],
        }

class ReActAgent:
    """ReAct Agent có sử dụng Thought-Action-Observation Loop"""
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.trace = []

    def run(self, user_input: str) -> dict:
        self.trace = []
        normalized_input = user_input.lower()
        actions = []

        flight_match = re.search(r"từ\s+([a-z]{3})\s+(?:đi|đến)\s+([a-z]{3})", normalized_input)
        asks_for_flight = bool(flight_match) or "chuyến bay nào" in normalized_input
        asks_for_weather = "thời tiết" in normalized_input or "mặc gì" in normalized_input

        if asks_for_flight:
            origin = flight_match.group(1).upper() if flight_match else "HAN"
            destination = flight_match.group(2).upper() if flight_match else "SGN"
            price_match = re.search(r"([\d,.]+)\s*triệu", normalized_input)
            max_price = 5000000
            if price_match:
                max_price = int(float(price_match.group(1).replace(",", ".")) * 1000000)
            actions.append(("get_flight_info", {"origin": origin, "destination": destination, "max_price": max_price}))

        if asks_for_weather:
            city_codes = {"sài gòn": "SGN", "hồ chí minh": "SGN", "đà nẵng": "DAD"}
            city_code = next(
                (code for city, code in city_codes.items() if city in normalized_input),
                next((code for code in ("SGN", "HAN", "DAD") if code.lower() in normalized_input), "SGN"),
            )
            actions.append(("get_weather_forecast", {"city_code": city_code}))

        if not actions:
            answer = f"Tôi chưa có công cụ phù hợp để xử lý yêu cầu: {user_input}"
            self.trace.append({"step": "final", "answer": answer})
            return {"status": "completed", "iterations": 1, "answer": answer, "trace": self.trace}

        observations = []
        for iteration, (tool_name, arguments) in enumerate(actions, start=1):
            if iteration > self.max_iterations:
                return {
                    "status": "max_iterations_reached",
                    "answer": "Không thể hoàn thành trong số bước tối đa.",
                    "iterations": self.max_iterations,
                    "trace": self.trace,
                }
            observation = TOOL_MAP[tool_name](**arguments)
            observations.append(observation)
            self.trace.append({
                "step": iteration,
                "action": {"name": tool_name, "args": arguments},
                "observation": observation,
            })

        answer_parts = []
        for observation in observations:
            if isinstance(observation, list):
                if observation:
                    flights = ", ".join(flight["flight_number"] for flight in observation)
                    answer_parts.append(f"Các chuyến bay phù hợp: {flights}.")
                else:
                    answer_parts.append("Không tìm thấy chuyến bay phù hợp.")
            elif isinstance(observation, dict) and "temperature_c" in observation:
                answer_parts.append(
                    f"Thời tiết {observation['city']}: {observation['temperature_c']}°C, "
                    f"{observation['recommendation']}."
                )

        answer = " ".join(answer_parts)
        if len(actions) > 1:
            self.trace.append({"step": len(self.trace) + 1, "final_answer": answer})
        return {
            "status": "completed",
            "iterations": len(self.trace),
            "answer": answer,
            "trace": self.trace,
        }

def main():
    user_query = "Tìm cho tôi chuyến bay từ HAN đi SGN dưới 2 triệu, rồi cho biết thời tiết SGN nên mặc gì?"
    
    print("=== RUNNING CHATBOT BASELINE ===")
    chatbot = ChatbotBaseline()
    print(chatbot.query(user_query))
    
    print("\n=== RUNNING REACT AGENT ===")
    agent = ReActAgent(max_iterations=5)
    result = agent.run(user_query)
    print("Result:", result)
    print("Trace Log:", json.dumps(agent.trace, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()