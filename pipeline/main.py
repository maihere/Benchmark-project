import csv
from pipeline.config import openai_client, claude_client, groq_client, openrouter_client

def ask(model: dict, user_message: str, system_prompt: str = "") -> str:
    """
    Sends a message to a model and returns the response text.
 
    Args:
        model: dict with keys — label, provider, model_id, and optionally token_params
               Example:
               {
                   "label": "o4-mini",
                   "provider": "openai",
                   "model_id": "o4-mini",
                   "token_params": {"max_completion_tokens": 4096}
               }
        user_message:  the question or prompt text to send
        system_prompt: the system instruction (loaded from prompt/*.txt files)
 
    Returns:
        The model's response as a plain string.
    """
    provider = model["provider"]
    model_id = model["model_id"]
 

    token_params  = model.get("token_params", {})
    temperature   = model.get("temperature")   # None means don't set it (required for o-series)

    if provider == "openai":
        return _ask_openai(openai_client, model_id, system_prompt, user_message, token_params, temperature)

    elif provider == "claude":
        return _ask_claude(model_id, system_prompt, user_message, token_params, temperature)

    elif provider == "groq":
        return _ask_groq(model_id, system_prompt, user_message, temperature)

    elif provider == "openrouter":
        return _ask_openai(openrouter_client, model_id, system_prompt, user_message, token_params, temperature)

    else:
        raise ValueError(f"Unknown provider: '{provider}'. Must be 'openai', 'claude', 'groq', or 'openrouter'.")
 
 
def _ask_openai(client, model_id: str, system_prompt: str, user_message: str,
                token_params: dict, temperature=None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    params = {"model": model_id, "messages": messages}

    if token_params:
        params.update(token_params)
    else:
        params["max_tokens"] = 1024

    # o-series models (o4-mini, o3) do not accept temperature — only add if explicitly set
    if temperature is not None:
        params["temperature"] = temperature

    response = client.chat.completions.create(**params)
    return response.choices[0].message.content
 
 
def _ask_claude(model_id: str, system_prompt: str, user_message: str,
                token_params: dict = None, temperature=None) -> str:
    kwargs = {
        "model":      model_id,
        "max_tokens": (token_params or {}).get("max_tokens", 1500),
        "messages":   [{"role": "user", "content": user_message}],
    }
    if system_prompt:
        kwargs["system"] = system_prompt
    if temperature is not None:
        kwargs["temperature"] = temperature

    response = claude_client.messages.create(**kwargs)
    return response.content[0].text
 
 
def _ask_groq(model_id: str, system_prompt: str, user_message: str, temperature=None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    params = {"model": model_id, "messages": messages, "max_tokens": 1024}
    if temperature is not None:
        params["temperature"] = temperature

    response = groq_client.chat.completions.create(**params)
    return response.choices[0].message.content
 
 
def load_questions(filepath: str, limit: int = None) -> list[dict]:
    """
    Reads questions from a CSV file and returns them as a list of dicts.
 
    Args:
        filepath: path to the CSV file (e.g. "data/questions.csv")
        limit:    if set, only return the first N questions (for pilot testing)
                  set to None to load all questions for the full benchmark run
 
    Returns:
        List of question dicts with keys matching CSV column names.
 
    Expected CSV columns:
        id, category, difficulty, language, source_url, question_text, accepted_answer
    """
    questions = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip template placeholder rows left over from the CSV template
            if "Paste" in row.get("question_text", ""):
                continue
            if not row.get("question_text", "").strip():      # Skip rows with empty question text
                continue
            questions.append(row)
 
    if limit is not None:
        questions = questions[:limit]
 
    return questions