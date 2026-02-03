from pydantic import BaseModel


class Skill(BaseModel):
    uri: str
    preferred_title: str
