import discord
from pydub import AudioSegment
import whisper
import asyncio
import os
from dotenv import load_dotenv
from  chatgpt import Role, Message, Chat
import time

load_dotenv()

intents = discord.Intents().all()
connecting_channels = dict()
bot = discord.Bot(intents=intents)

Token = os.getenv("DISCORD_TOKEN")

model = whisper.load_model("medium")


def get_voice_client(channel_id: int) -> discord.VoiceClient | None:
    for client in bot.voice_clients:
        if client.channel.id == channel_id:
            return client
    else:
        return None

@bot.event
async def on_ready():
    print('connected')

@bot.slash_command(name="join", description="ボイスチャンネルに参加するよ")
async def join(interaction: discord.Interaction):
    await interaction.response.defer()
    print(f"join:{interaction.channel}")
    connecting_channels[interaction.channel_id]=Chat(os.getenv("OPENAI_API_KEY"))
    await interaction.followup.send('ボイスチャンネルに参加します')
    try:
        await interaction.channel.connect()
    except Exception as e:
        connecting_channels[interaction.channel_id]
        await interaction.followup.send(f"参加中に異常が発生しました\n```{e}```")


@bot.command(name="dc", description="ボイスチャンネルから退出するよ")
async def dc(interaction: discord.Interaction):
    await interaction.response.defer()
    client: discord.VoiceClient | None = get_voice_client(
        interaction.channel_id)

    if client:
        if interaction.channel_id in connecting_channels:
            chat:Chat = connecting_channels[interaction.channel_id]
            history=chat.make_log()
            with open("log.txt","w",encoding='utf8') as f:
                for msg in history:
                    f.write(msg["content"]+"\n")
            await interaction.followup.send(file=discord.File("log.txt"))

            del connecting_channels[interaction.channel_id]
        await client.disconnect()
        await interaction.followup.send('ボイスチャンネルからログアウトしました')
    else:
        await interaction.followup.send('ボイスチャンネルに参加していません')


@bot.slash_command()
async def start_record(ctx: discord.ApplicationContext):
    await ctx.respond("録音開始...")
    # コマンドを使用したユーザーのボイスチャンネルに接続
    try:
        ctx.voice_client.start_recording(discord.sinks.MP3Sink(), finished_callback, ctx)
        await asyncio.sleep(10)
        ctx.voice_client.stop_recording()
            
    except AttributeError:
        await ctx.respond("ボイスチャンネルに入ってください。")
        return




@bot.slash_command()
async def stop_recording(ctx: discord.ApplicationContext):
    # 録音停止
    ctx.voice_client.stop_recording()
    await ctx.respond("録音終了!")

# 録音終了時に呼び出される関数

async def getTransacription(filename: str):
    user = await bot.fetch_user(int(filename.split("_")[0]))
    display_name = user.display_name
    result = model.transcribe(filename, language='ja')
    return display_name, result["text"]


async def finished_callback(sink: discord.sinks.MP3Sink, ctx: discord.ApplicationContext):
    msg = ""
    # 録音したユーザーの音声を取り出す
    for user_id, audio in sink.audio_data.items():
        # mp3ファイルとして書き込み。その後wavファイルに変換。
        song = AudioSegment.from_file(audio.file, format="mp3")
        filename = f"{user_id}_{time.time()}.mp3"
        song.export(filename, format='mp3')
        trans = await getTransacription(filename)
        os.remove(filename)
        msg += trans[0] +  ":" + trans[1] + '\n'
    if ctx.channel_id in connecting_channels:
        chat :Chat = connecting_channels[ctx.channel_id]
        chat.add(msg,Role.user)
    print(msg)
    if msg=="":
        msg = "誰も喋ってないよ"
    # メッセージを送る
    await ctx.respond(msg)
    ctx.voice_client.start_recording(discord.sinks.MP3Sink(), finished_callback, ctx)


@bot.command(name="now", description="現在のチャットの要点を整理するよ")
async def now(interaction: discord.Interaction):
    await interaction.response.defer()
    if interaction.channel_id in connecting_channels:
        chat = connecting_channels[interaction.channel_id]
        await interaction.followup.send("要点を整理しています...")
        reply:Message = chat.send("現在の会話ログはここまでです、この会議の要点を整理します。",Role.system)
        await interaction.followup.send(reply.content)
    else:
        await interaction.followup.send("ボイスチャンネルに参加していません")

bot.run(Token)
