import codecs
import random
import argh
import openai

# Load openai API key from key.txt file
def load_api_key(file_path):
    """
    Load OpenAI API key from a file.

    Args:
        file_path (str): Path to the file containing the OpenAI API key.

    Returns:
        str: The OpenAI API key.
    """
    with open(file_path, 'r') as f:
        return f.read().strip()


def rewrite_paragraphs(input_file, output_file, model="gpt-4o-mini", candidate_topics='\topics-example.txt', temperature=1.1, key_path="key.txt", verbose=False,
                       limit=0, resample_per_topic=3):
    """
    Rewrites paragraphs in a text file using OpenAI's GPT-4.1-mini model.

    Args:
        input_file (str): Path to the input text file containing paragraphs to rewrite.
        output_file (str): Path to the output text file to save rewritten paragraphs.
        model (str): The OpenAI model to use for rewriting.
        temperature (float): Sampling temperature for the model. Default is 0.7.
    """
    openai.api_key = load_api_key(key_path)  # Load API key from the specified file

    if 'qwen' in model:
        openai_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        openai.api_base = openai_base_url

    candidate_topics = [l.strip() for l in codecs.open(candidate_topics, 'r', encoding='utf-8').readlines() if l.strip()]

    with open(input_file, 'r') as f:
        # organize paragraphs with filenames. each line is filename\t paragraph:
        filename_to_content = {}
        filenames = []
        raw_chunks = [line.strip('\n') for line in f.readlines()]
        paragraphs = [line.split('\t') for line in raw_chunks]
        for fname, para in paragraphs:
            if fname not in filename_to_content:
                filename_to_content[fname] = []
                filenames.append(fname)
            filename_to_content[fname].append(para)

    # for filename in filenames:
    #     print(filename)

    # Use few-shot prompting to rewrite paragraphs with 10 different topics, keeping a similar and casual tone with the reference.
    fout = codecs.open(output_file, 'w', encoding='utf-8')
    random.seed(42)

    if limit > 0:
        candidate_topics = candidate_topics[:limit]
    for this_topic in candidate_topics:
        print("Generating for topic:", this_topic)
        for idx in range(resample_per_topic):
            samples = random.sample(paragraphs, 3)
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Your will be given a topic and compose a casual chatting-style paragraph."}]
            for sample in samples:
                topic, content = sample
                topic = topic.split('-')[0].split('.wav')[0]
                if 'ishowspeed' in topic:
                    topic = 'ishowspeed travels in China'
                # print(idx, f"Topic: {topic}\n", f"Content: {content}")
                messages.append({"role": "user", "content": f"Topic: {topic}"})
                messages.append({"role": "assistant", "content": f"{content}"})

            messages.append({"role": "user", "content": f"Topic: '{this_topic}"})

            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            try:
                result = response['choices'][0]['message']['content']
            except KeyError:
                continue
            for para in result.split('\n'):
                if not para.strip():
                    continue
                para = para.strip()
                print(f"{this_topic}:\t{para}", file=fout)
            fout.flush()
    fout.close()


if __name__ == "__main__":
    argh.dispatch_command(rewrite_paragraphs)

# python rewrite_paragraphs.py all-seed-notebook-asrs.txt rewritten-v1-nano-320.txt -k openai-key.txt -m gpt-4.1-nano -c topics-300.txt
