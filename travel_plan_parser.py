from langchain_together import Together
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List
import os

# Set your Together API key
os.environ["TOGETHER_API_KEY"] = "3ffa218a6e676b474ba7e5988c845b3f8e0770473b8249fc53a3ec3cce86dc74"

class TravelEvent(BaseModel):
    date: str = Field(description="The date of the event in YYYY-MM-DD format")
    start_time: str = Field(description="The start time of the event in HH:MM format")
    end_time: str = Field(description="The end time of the event in HH:MM format")
    title: str = Field(description="The title of the event")
    description: str = Field(description="A brief description of the event")

class TravelPlan(BaseModel):
    events: List[TravelEvent] = Field(description="A list of events in the travel plan")

def parse_travel_plan(travel_plan_text: str, start_date: str, num_days: int) -> TravelPlan:
    parser = PydanticOutputParser(pydantic_object=TravelPlan)

    prompt = PromptTemplate(
        template="Extract the daily events from the following travel plan. The trip starts on {start_date} and lasts for {num_days} days.\n\n{travel_plan}\n\n{format_instructions}\n",
        input_variables=["travel_plan", "start_date", "num_days"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    llm = Together(
        model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        temperature=0,
        max_tokens=1024
    )

    _input = prompt.format_prompt(travel_plan=travel_plan_text, start_date=start_date, num_days=num_days)
    output = llm(_input.to_string())

    try:
        return parser.parse(output)
    except Exception as e:
        print(f"Failed to parse the model's response: {e}")
        return TravelPlan(events=[])