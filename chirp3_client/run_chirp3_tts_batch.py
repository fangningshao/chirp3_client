import json
import argh
import os
import re
from google.cloud import texttospeech_v1beta1 as texttospeech
from google.oauth2.credentials import Credentials
from google.api_core.client_options import ClientOptions
from typing import Iterator

# 请替换为您的 Google Cloud Project ID
PROJECT_ID = ""

# 请替换为您的静态 token
STATIC_TOKEN = ""  # zf gmail 固定token

# Read project_id and token from chirp3-keys.json in the same directory with the script:
try:
    keys_file = os.path.join(os.path.dirname(__file__), 'chirp3-keys.json')
    with open(keys_file, 'r') as f:
        keys = json.load(f)
        PROJECT_ID = keys['project_id']
        STATIC_TOKEN = keys['token']
    print("Loaded project_id and token from chirp3-keys.json")
except FileNotFoundError:
    print("chirp3-keys.json not found, using default values")
    pass  # 如果文件不存在，则继续使用默认值

TTS_LOCATION = "global"

API_ENDPOINT = (
    f"{TTS_LOCATION}-texttospeech.googleapis.com"
    if TTS_LOCATION != "global"
    else "texttospeech.googleapis.com"
)

client = texttospeech.TextToSpeechClient(
    client_options=ClientOptions(
        api_endpoint=API_ENDPOINT,
        api_key=STATIC_TOKEN)
)

def get_voice_from_name(voice_name='Aoede'):
    # Control voice
    voice = voice_name  # @param ["Aoede", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Zephyr"]
    language_code = "en-US"  # @param [ "de-DE", "en-AU", "en-GB", "en-IN", "en-US", "fr-FR", "hi-IN", "pt-BR", "ar-XA", "es-ES", "fr-CA", "id-ID", "it-IT", "ja-JP", "tr-TR", "vi-VN", "bn-IN", "gu-IN", "kn-IN", "ml-IN", "mr-IN", "ta-IN", "te-IN", "nl-NL", "ko-KR", "cmn-CN", "pl-PL", "ru-RU", "th-TH"]
    voice_name = f"{language_code}-Chirp3-HD-{voice}"
    voice = texttospeech.VoiceSelectionParams(
        name=voice_name,
        language_code=language_code,
    )
    return voice


DEFAULT_VOICE = 'en-US-Chirp3-HD-Aoede'  # 默认语音设置

def synthesize_speech_with_chirp3(prompt, output_filename="audio.mp3", verbose=False, output_textfile=None, voice=None):
    """使用 Chirp 3 合成带有特殊标记的语音。

    Args:
        prompt: 要合成的文本，可以包含 Chirp 3 的特殊标记。
        output_filename: 保存合成语音的文件名。
    """
    try:
        # # 使用静态 token 创建凭据
        # credentials = Credentials(STATIC_TOKEN)
        # print("DEBUG", credentials)

        # # 实例化 Text-to-Speech 客户端
        # client = texttospeech.TextToSpeechClient(credentials=credentials)

        # 设置要合成的文本
        input_text = texttospeech.SynthesisInput(text=prompt)
        if verbose:
            print(f'Input text prompt: {input_text}')
        if output_textfile:
            with open(output_textfile, 'w', encoding='utf-8') as f:
                f.write(prompt)

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        # 调用 Text-to-Speech 服务合成语音
        response = client.synthesize_speech(
            request={
                "input": input_text,
                "voice": voice or DEFAULT_VOICE,
                "audio_config": audio_config}
        )

        # 将合成的音频内容写入文件
        with open(output_filename, "wb") as out:
            out.write(response.audio_content)
            if verbose:
                print(f'音频内容已保存到: {output_filename}')

    except Exception as e:
        print(f"发生错误: {e}")


def single(input_text='Hi hi, I am chirp 3!', output_filename="audio.wav", verbose=False):
    """主函数，处理命令行参数并调用合成函数。

    Usage:
        python run_chirp3_tts_batch.py single "Hi hi, I am chirp 3!" output.wav -v

    Args:
        input_text: 要合成的文本，可以包含 Chirp 3 的特殊标记。
        output_filename: 保存合成语音的文件名。
        verbose: 是否打印详细信息。
    """
    synthesize_speech_with_chirp3(input_text, output_filename, verbose=verbose)


def batch_texts_to_outfiles(input_texts: Iterator[str], output_filenames: Iterator[str], output_textfiles: Iterator[str], verbose=False, limit=0, voice=None):
    """批量处理函数，处理命令行参数并调用合成函数。"""
    lines = zip(input_texts, output_filenames, output_textfiles)
    if limit > 0:
        lines = list(lines)[:limit]
    for input_text, output_filename, output_textfile in lines:
        synthesize_speech_with_chirp3(input_text, output_filename, verbose=verbose, output_textfile=output_textfile, voice=voice)


voice = "Aoede"  # @param ["Aoede", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Zephyr"]

def batch(input_file: str, output_dir: str, verbose=False, limit=0, textdir: str = None, filename_prefix='chrp', num_digits=4, voices='Aoede', start_idx=0):
    """批量处理函数，处理命令行参数并调用合成函数。
    Usage:
        python run_chirp3_tts_batch.py batch input.txt output_dir

    Args:
        input_file: 输入文件，包含要合成的文本，每行一个。
        output_dir: 输出目录，用于保存合成的音频文件。
    """
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        input_texts = f.readlines()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    multivoice = False
    voices_to_synthesize = []
    for voice_name in voices.split(','):
        voice_name = voice_name.strip()
        voice = get_voice_from_name(voice_name=voice_name)
        voices_to_synthesize.append(voice)

    if len(voices_to_synthesize) > 1:
        multivoice = True

    root_output_dir = output_dir
    for voice in voices_to_synthesize:
        if multivoice:
            print("DEBUG: Using voice:", voice.name)
            output_dir = os.path.join(root_output_dir, voice.name.split('-')[-1])
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
        # 生成输出文件名 change {i} to 4 digits like 0001, 0002, 0003
        output_filenames = [os.path.join(output_dir, f"{filename_prefix}{str(i).zfill(num_digits)}.wav") for i in range(len(input_texts))]
        # .txt files as well inside textdir
        textdir = textdir or output_dir
        if not os.path.exists(textdir):
            os.makedirs(textdir)
        output_textfiles = [os.path.join(textdir, f"{filename_prefix}{str(i).zfill(num_digits)}.txt") for i in range(len(input_texts))]

        if start_idx > 0:
            input_texts = input_texts[start_idx:]
            output_filenames = output_filenames[start_idx:]
            output_textfiles = output_textfiles[start_idx:]

        # 执行批量处理
        batch_texts_to_outfiles(input_texts, output_filenames, output_textfiles, verbose=verbose, limit=limit, voice=voice)

if __name__ == "__main__":
    argh.dispatch_commands([single, batch])


# python batch\run_chirp3_tts_batch.py batch test-input-2.txt test-input-2-chirp3 --voices=Aoede,Kore,Leda,Zephyr
