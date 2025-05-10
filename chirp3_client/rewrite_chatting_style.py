import time
import codecs
import random
import argh
import openai

SYSTEM_PROMPT = """Your will be given a paragraph and rewrite it to a more natural, spoken-style paragraph that will be used for TTS without changing its original meaning. The rewritten paragraph should be casual and conversational, as if it were spoken by a human.

Please actively use the following techniques to make the paragraph sound more natural:
- Periods (.): Indicate a full stop and a longer pause. Use them to separate complete thoughts and create clear sentence boundaries.
- Commas (,): Signal shorter pauses within sentences. Use them to separate clauses, list items, or introduce brief breaks for breath.
- Ellipses (...): Represent a longer, more deliberate pause. They can indicate trailing thoughts, hesitation, or a dramatic pause.
    - Example: "And then... it happened."
- Hyphens (-): Can be used to indicate a brief pause or a sudden break in thought.
- Example: "I wanted to say - but I couldn't."
- Use ellipses, commas, or hyphens to create pauses in places where a human speaker would naturally pause for breath or emphasis.
- Actively and diversely use disfluencies including: um, uh, huh, uh-huh, ah, aha, eww.
"""

FEW_SHOT_PROMPTS = [
    ("""The product is now available. We have new features. It is very exciting.""",
     """The product is now available... and we've added some exciting new features. It's, well, it's very exciting."""),
    ("""This is an automated confirmation message. Your reservation has been processed. The following details pertain to your upcoming stay. Reservation number is 12345. Guest name registered is Anthony Vasquez Arrival date is March 14th. Departure date is March 16th. Room type is Deluxe Suite. Number of guests is 1 guest. Check-in time is 3 PM. Check-out time is 11 AM. Please note, cancellation policy requires notification 48 hours prior to arrival. Failure to notify within this timeframe will result in a charge of one night's stay. Additional amenities included in your reservation are: complimentary Wi-Fi, access to the fitness center, and complimentary breakfast. For any inquiries, please contact the hotel directly at 855-555-6689 Thank you for choosing our hotel.""",
    """Hi Anthony Vasquez! We're so excited to confirm your reservation with us! Well, you're all set for your stay from... March 14th to March 16th in our beautiful Deluxe Suite. That's for 1 guest, huh? Your confirmation number is - 12345, um, just in case you need it. So... just a quick reminder, check-in is at 3 PM, and check-out is at, well, 11 AM. Now, just a heads-up about our cancellation policy... if you need to cancel, uh, just let us know at least 48 hours before your arrival, okay? Otherwise, eww... there'll be a charge for one night's stay, huh. And to make your stay even better, you'll have complimentary Wi-Fi, access to our fitness center, and a delicious complimentary breakfast each morning, yay! Well... if you have any questions at all, please don't hesitate to call us at 855-555-6689. We can't wait to welcome you to the hotel, cheers!"""),
]



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


def rewrite_paragraphs(input_file, output_file, model="gpt-4.1-mini", temperature=0.7, key_path="key.txt", verbose=False, limit=0, start_idx=0):
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

    if start_idx > 0:
        fout = codecs.open(output_file, 'a', encoding='utf-8')
    else:  # if start_idx not specified, overwrite the file
        fout = codecs.open(output_file, 'w', encoding='utf-8')

    input_lines = [l.strip() for l in codecs.open(input_file, 'r', encoding='utf-8').readlines() if l.strip()]

    if limit > 0:
        input_lines = input_lines[:limit]

    for idx, line in enumerate(input_lines):
        if idx < start_idx:
            continue

        parts = line.split('\t')
        if len(parts) != 2:
            print("Error: Invalid input line format:", line)
            continue
        topic, content = parts
        topic = topic.split(':')[0]

        print(f"[{idx}] Generating for topic:", topic)

        messages=[{"role": "system", "content": SYSTEM_PROMPT}]

        for qa_pair in FEW_SHOT_PROMPTS:
            if verbose: print("DEBUG QA:", qa_pair)
            messages.append({"role": "user", "content": "Rewrite the following paragraph: " + qa_pair[0]})
            messages.append({"role": "assistant", "content": qa_pair[1]})

        messages.append({"role": "user", "content": "Rewrite the following paragraph: " + content})
        if verbose:
            print("DEBUG MSGS:", messages)

        # Retry for 3 times if the API call fails
        success = False
        for _ in range(3):
            try:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
                success = True
                break
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                print(f"Error: {e}. Retrying...")
                # Sleep before retrying
                time.sleep(5)
                continue

        if not success:
            print("Failed to get a response after 3 attempts. IDX:", idx)
            break

        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        try:
            result = response['choices'][0]['message']['content']
            if verbose:
                print("DEBUG RESULT:", response)
        except KeyError:
            continue
        for para in result.split('\n'):
            if not para.strip():
                continue
            para = para.strip()
            print(f"{topic}:\t{para}", file=fout)
        fout.flush()
    fout.close()


if __name__ == "__main__":
    argh.dispatch_command(rewrite_paragraphs)

# start from line 690
# python rewrite_chatting_style.py rewritten-v1-nano-300.txt rewritten-chatting-v1-4o-mini.txt -k openai-key.txt -m gpt-4o-mini -l 10 -v
# python rewrite_chatting_style.py rewritten-v1-nano-300.txt rewritten-chatting-v1-4o-mini.txt -k openai-key.txt -m gpt-4o-mini -l 10 -v --start-idx 690
