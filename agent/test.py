from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel

load_dotenv()

class Person(BaseModel):
    name: str
    age: int

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
)

resp = llm.with_structured_output(Person).invoke(
    "John is 25 years old."
)

print(resp)