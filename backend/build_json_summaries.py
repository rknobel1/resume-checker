from ollama_client import ask_ollama
import json

def extract_json(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        print("Unable to parse resume content into JSON")


def build_resume_summary_prompt(parsed_text: str) -> str:
    prompt = """
        Your task is to take the given data and split the content into sections.

        IMPORTANT: RETURN VALID JSON. The JSON returned should take the following format:

        {
        "Contact": [
            {
            "Phone": "",
            "Email": "",
            "Website/Portfolio": "",
            "Social/Other": [""]
            }
        ],
        "Summary": "",
        "Education": [
            {
            "University": "",
            "Degree": "",
            "Dates": "",
            "Minor": "",
            "GPA": ""
            }
        ],
        "Experience": [
            {
            "Title": "",
            "Company": "",
            "Dates": "",
            "Details": [""]
            }
        ],
        "Projects": [
            {
            "Title": "",
            "Technologies": [""],
            "Details": [""]
            }
        ],
        "Skills": [
            {
            "Category": "",
            "Skills": [""]
            }
        ],
        "Relevant Courses": [""],
        "Awards": [
            {
            "Award": "",
            "Details": [""]
            }
        ],
        "Certifications": [
            {
            "Certification": "",
            "Details": [""]
            }
        ]
        }

        For any section or data that is missing, leave empty. Do NOT make up any information.

        The data you are given is displayed here:

        __PARSED_TEXT__
        """
    return prompt.replace("__PARSED_TEXT__", parsed_text)


def build_resume_json_summary(parsed_text: str) -> str:
    try:
        prompt = build_resume_summary_prompt(parsed_text)

        raw = ask_ollama(prompt, task="rewrite_generation")
        raw_json = json.loads(raw)

        return raw_json

    except Exception:
        print("Error parsing pdf resume extraction into JSON")




def build_jd_summary_prompt(parsed_text: str) -> str:
    prompt = """
        Your task is to take the given job description and determine the following information: 
            1. What are the REQUIREMENTS for this job?  
            2. What are the PREFERENCES for this job?
            3. What skills are REQUIRED for this job?
            4. What skills are PREFERRED for this job? 

        Do not duplicate skills

        IMPORTANT: RETURN VALID JSON. The JSON returned should take the following format:

        {
            "required_lines": [""],
            "preferred_lines": [""],
            "other_lines": [""],
            "required_skills": [""],
            "preferred_skills": [""],
            "all_skills": [""],
        }

        For any section or data that is missing, leave empty. Do NOT make up any information.

        The job description is displayed here:

        __PARSED_TEXT__
        """
    return prompt.replace("__PARSED_TEXT__", parsed_text)


def build_jd_json_summary(parsed_text: str) -> str:
    try:
        prompt = build_jd_summary_prompt(parsed_text)

        raw = ask_ollama(prompt, task="rewrite_generation")
        raw_json = json.loads(raw)

        return raw_json

    except Exception:
        print("Error parsing pdf resume extraction into JSON")