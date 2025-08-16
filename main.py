import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
    handlers=[handler]
)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

game_states = {}

@bot.event
async def on_ready():
    """Sự kiện này chạy khi bot đã kết nối thành công với Discord."""
    logging.info(f'Bot đã đăng nhập với tên {bot.user}')
    logging.info('-----------------------------------------')
    print(f'Bot đã đăng nhập với tên {bot.user}')
    print("Bot đã sẵn sàng và commands đã được load!")

@bot.event
async def on_message(message):
    """Sự kiện này chạy mỗi khi có một tin nhắn được gửi ở bất kỳ đâu bot có thể thấy."""
    if message.author == bot.user:
        return
    
    channel_id = message.channel.id
    if channel_id in game_states and game_states[channel_id]['is_active']:
        state = game_states[channel_id]

        if message.author == state['last_player']:
            return
    
        word = message.content.strip().lower()
        if not word:
            await message.channel.send("Bạn không thể gửi từ rỗng!")
            return
        last_word = state['last_word']
        if last_word and not word.startswith(last_word[-1]):
            await message.channel.send(f"Từ '{word}' không hợp lệ! Nó phải bắt đầu bằng chữ '{last_word[-1]}'.")
            return
    
        await message.add_reaction('✅')

        state['last_word'] = word
        state['last_player'] = message.author

        await message.channel.send(f"Hay lắm! Từ tiếp theo phải bắt đầu bằng **{word[-1].upper()}**. Mời mọi người!")

    await bot.process_commands(message)

@bot.command(name='noichu')
async def start_channel_game(ctx):
    """Bắt đầu minigame nối chữ."""
    channel_id = ctx.channel.id

    if channel_id in game_states and game_states[channel_id]['is_active']:
        await ctx.send("Minigame nối chữ đã được bắt đầu trong kênh này rồi!")
        return
    
    game_states[channel_id] = {
        'last_word': None,
        'last_player': None,
        'is_active': True
    }

    await ctx.send(
        f"🎉 Minigame nối chữ đã bắt đầu! 🎉\n"
        f"Luật chơi: Nối từ bắt đầu bằng chữ cái cuối của từ trước đó. Bất kỳ ai cũng có thể tham gia!\n"
        f"Mời người đầu tiên ra từ!"
    )

@bot.command(name='dunggame')
async def stop_channel_game(ctx):
    """Dừng minigame nối chữ."""
    channel_id = ctx.channel.id

    if channel_id in game_states and game_states[channel_id]['is_active']:
        del game_states[channel_id]
        await ctx.send("Minigame nối chữ đã dừng lại. Cảm ơn mọi người đã tham gia!")
    else:
        await ctx.send("Không có minigame nối chữ nào đang diễn ra trong kênh này.")

@bot.event
async def on_command_error(ctx, error):
    print(f"Command error: {error}")
    logging.error(f"Command error: {error}")

if __name__ == "__main__":
    if not token:
        print("ERROR: DISCORD_TOKEN không được tìm thấy trong file .env!")
    else:
        print("Đang khởi động bot...")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)