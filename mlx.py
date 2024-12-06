def get_mlx_model(model_name: str, chat_template_name: [str, None] = None):
    """Load MLX model + tokenizer and apply chat template."""
    from mlx_lm import load

    mlx_model, mlx_tokenizer = load(
        f"mlx-community/{model_name}",
        tokenizer_config={
            # "eos_token": "<|eot_id|>",
            "trust_remote_code": True
        },
    )
    if chat_template_name is not None:
        chat_template = open(f"utils/{chat_template_name}").read()
        chat_template = chat_template.replace("    ", "").replace("\n", "")
        mlx_tokenizer.chat_template = chat_template
    return mlx_model, mlx_tokenizer


def run_mlx_query(
    system_prompt: str,
    user_prompt: str,
    mlx_model,
    mlx_tokenizer,
    max_tokens: int = 500,
):
    """Summarize a paper by segments with MLX models."""
    from mlx_lm import generate

    messages = [("system", system_prompt), ("user", user_prompt)]
    messages = [{"role": role, "content": content} for role, content in messages]

    prompt = mlx_tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    summary = generate(
        mlx_model,
        mlx_tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        temp=0.9,
        # repetition_penalty=1.05,
        verbose=False,
    )

    return summary


def mlx_query_pipeline(
    system_prompt: str,
    user_prompt: str,
    model_name: str = "Meta-Llama-3-8B-Instruct",
    chat_template_name: [str, None] = None,
    max_tokens: int = 1500,
):
    """Run a query pipeline with MLX models."""
    mlx_model, mlx_tokenizer = get_mlx_model(model_name, chat_template_name)
    summary = run_mlx_query(
        system_prompt, user_prompt, mlx_model, mlx_tokenizer, max_tokens
    )

    return summary