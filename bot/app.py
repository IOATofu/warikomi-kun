import discord
from pydub import AudioSegment
from discord import Embed, Interaction, ui
import whisper
import asyncio

intents = discord.Intents().all()
connecting_channels = set()
bot = discord.Bot(intents=intents)

Token = ""

model = whisper.load_model("medium")


def get_voice_client(channel_id: int) -> discord.VoiceClient | None:
    for client in bot.voice_clients:
        if client.channel.id == channel_id:
            return client
    else:
        return None


@bot.slash_command(name="join", description="ボイスチャンネルに参加するよ")
async def join(interaction: Interaction):
    await interaction.response.defer()
    print(f"join:{interaction.channel}")
    connecting_channels.add(interaction.channel_id)
    await interaction.followup.send('ボイスチャンネルに参加します')
    try:
        await interaction.channel.connect()
    except Exception as e:
        connecting_channels.remove(interaction.channel_id)
        await interaction.followup.send(f"参加中に異常が発生しました\n```{e}```")


@bot.command(name="dj", description="ボイスチャンネルから退出するよ")
async def dc(interaction: Interaction):
    await interaction.response.defer()
    client: discord.VoiceClient | None = get_voice_client(
        interaction.channel_id)

    if client:
        await client.disconnect()
        await interaction.followup.send('ボイスチャンネルからログアウトしました')
    else:
        await interaction.followup.send('ボイスチャンネルに参加していません')


@bot.slash_command()
async def start_record(ctx: discord.ApplicationContext):

    # コマンドを使用したユーザーのボイスチャンネルに接続
    try:
        await ctx.respond("録音開始...")
    except AttributeError:
        await ctx.respond("ボイスチャンネルに入ってください。")
        return

    # 録音開始。mp3で帰ってくる。wavだとなぜか壊れる。
    ctx.voice_client.start_recording(
        discord.sinks.MP3Sink(), finished_callback, ctx)


@bot.slash_command()
async def stop_recording(ctx: discord.ApplicationContext):
    # 録音停止
    ctx.voice_client.stop_recording()
    await ctx.respond("録音終了!")

# 録音終了時に呼び出される関数


async def getTransacription(user_id: int):
    user = await bot.fetch_user(user_id)
    display_name = user.display_name
    result = model.transcribe(str(user_id) + ".wav")
    return display_name, result["text"]


async def finished_callback(sink: discord.sinks.MP3Sink, ctx: discord.ApplicationContext):
    msg = ""
    # 録音したユーザーの音声を取り出す
    for user_id, audio in sink.audio_data.items():
        # mp3ファイルとして書き込み。その後wavファイルに変換。
        song = AudioSegment.from_file(audio.file, format="mp3")
        song.export(f"./{user_id}.wav", format='wav')
        trans = await getTransacription(user_id)
        msg += trans[0] + ":" + trans[1] + '\n'
    print(msg)
    # メッセージを送る
    await ctx.respond(msg)


async def main():
    # start the client
    async with bot:
        print("Bot started")
        await bot.start(Token)

asyncio.run(main())
