import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
import aiohttp
import asyncio

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
logging.basicConfig(
    level=logging.WARMING,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
    handlers=[handler] 
)

logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

game_states = {}

async def is_valid_english_word(word: str) -> bool:
    """Kiểm tra xem từ có phải là từ tiếng Anh hợp lệ không."""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    return len(data) > 0
                else:
                    return False
    except Exception as e:
        logging.error(f"Lỗi khi kiểm tra từ '{word}': {e}")
        return True

@bot.event
async def on_ready():
    """Sự kiện này chạy khi bot đã kết nối thành công với Discord."""
    print(f'✅ Bot đã đăng nhập: {bot.user}')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Đã sync {len(synced)} slash commands')
        print('✅ Bot sẵn sàng hoạt động!')
        print('=' * 40)
            
    except Exception as e:
        print(f'❌ Không thể sync slash commands: {e}')
        logging.error(f"Không thể sync slash commands: {e}")

@bot.event
async def on_message(message):
    """Sự kiện này chạy mỗi khi có một tin nhắn được gửi ở bất kỳ đâu bot có thể thấy."""
    if message.author == bot.user:
        return

    await bot.process_commands(message)
    
    channel_id = message.channel.id
    if channel_id in game_states and game_states[channel_id]['is_active']:
        state = game_states[channel_id]

        if message.author == state['last_player']:
            return
    
        word = message.content.strip().lower()
        if not word:
            await message.channel.send("Bạn không thể gửi từ rỗng!")
            return

        if not word.isalpha():
            await message.channel.send(f"Từ '{word}' không hợp lệ! Chỉ được sử dụng chữ cái tiếng Anh.")
            return

        if len(word) < 2:
            await message.channel.send(f"Từ '{word}' quá ngắn! Từ phải có ít nhất 2 chữ cái.")
            return
        if len(word) > 15:
            await message.channel.send(f"Từ '{word}' quá dài! Từ không được vượt quá 15 chữ cái.")
            return

        last_word = state['last_word']
        if last_word and not word.startswith(last_word[-1]):
            await message.channel.send(f"Từ '{word}' không hợp lệ! Nó phải bắt đầu bằng chữ '{last_word[-1].upper()}'.")
            return

        try:
            checking_msg = await message.channel.send("🔍 Đang kiểm tra từ điển...")
            is_valid = await is_valid_english_word(word)

            if not is_valid:
                await checking_msg.edit(content=f"❌ Từ '{word}' không có nghĩa trong tiếng Anh! Hãy thử từ khác.")
                return
            
            await checking_msg.delete()
            await message.add_reaction('✅')

            state['last_word'] = word
            state['last_player'] = message.author

            next_letter = word[-1].upper()
            await message.channel.send(f"Hay lắm! Từ tiếp theo phải bắt đầu bằng **{next_letter}**. Mời mọi người!")
            
        except Exception as e:
            logging.error(f"Lỗi khi xử lý từ '{word}': {e}")
            await message.channel.send("❌ Có lỗi xảy ra khi kiểm tra từ. Hãy thử lại!")

@bot.tree.command(name="noichu", description="Bắt đầu minigame nối chữ")
async def start_channel_game(interaction: discord.Interaction):
    """Bắt đầu minigame nối chữ."""
    try:
        channel_id = interaction.channel.id
        if channel_id in game_states and game_states[channel_id]['is_active']:
            await interaction.response.send_message("Minigame nối chữ đã được bắt đầu trong kênh này rồi!", ephemeral=True)
            return

        game_states[channel_id] = {
            'last_word': None,
            'last_player': None,
            'is_active': True
        }

        embed = discord.Embed(
            title="🎉 Minigame Nối Chữ Đã Bắt Đầu! 🎉",
            description=f"**Được khởi tạo bởi:** {interaction.user.mention}\n\n**Luật chơi:**\n• Nối từ bắt đầu bằng chữ cái cuối của từ trước đó\n• Từ phải có nghĩa trong tiếng Anh\n• Từ phải có từ 2-15 chữ cái\n• Bất kỳ ai cũng có thể tham gia!\n\n**Mời người đầu tiên ra từ!**",
            color=discord.Color.green()
        )
        embed.set_footer(text="Sử dụng /dunggame để dừng game")

        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logging.error(f"Lỗi trong start_channel_game: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("Có lỗi xảy ra khi bắt đầu game!", ephemeral=True)

@bot.tree.command(name="dunggame", description="Dừng minigame nối chữ")
async def stop_channel_game(interaction: discord.Interaction):
    """Dừng minigame nối chữ."""
    try:
        channel_id = interaction.channel.id

        if channel_id in game_states and game_states[channel_id]['is_active']:
            del game_states[channel_id]
            embed = discord.Embed(
                title="🛑 Game Đã Dừng",
                description=f"**Dừng bởi:** {interaction.user.mention}\n\nMinigame nối chữ đã dừng lại. Cảm ơn mọi người đã tham gia!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Không có minigame nối chữ nào đang diễn ra trong kênh này.", ephemeral=True)
            
    except Exception as e:
        logging.error(f"Lỗi trong stop_channel_game: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("Có lỗi xảy ra khi dừng game!", ephemeral=True)

@bot.tree.command(name="checkgame", description="Kiểm tra trạng thái game hiện tại")
async def check_game_status(interaction: discord.Interaction):
    """Kiểm tra trạng thái game hiện tại."""
    try:
        channel_id = interaction.channel.id

        if channel_id in game_states and game_states[channel_id]['is_active']:
            state = game_states[channel_id]
            embed = discord.Embed(
                title="✅ Game Đang Chạy",
                description=f"**Được kiểm tra bởi:** {interaction.user.mention}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Từ cuối cùng", value=state['last_word'] or "Chưa có", inline=True)
            embed.add_field(name="Người chơi cuối", value=state['last_player'].mention if state['last_player'] else "Chưa có", inline=True)
            
            if state['last_word']:
                next_letter = state['last_word'][-1].upper()
                embed.add_field(name="Chữ cái tiếp theo", value=next_letter, inline=True)

            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Không Có Game",
                description=f"**Được kiểm tra bởi:** {interaction.user.mention}\n\nKhông có game nào đang chạy trong kênh này.\nSử dụng `/noichu` để bắt đầu game mới!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            
    except Exception as e:
        logging.error(f"Lỗi trong check_game_status: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("Có lỗi xảy ra khi kiểm tra trạng thái game!", ephemeral=True)

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Xử lý lỗi slash commands."""
    logging.error(f"Slash command error: {error}")
    print(f"Slash command error: {error}")
    
    if not interaction.response.is_done():
        try:
            await interaction.response.send_message("Có lỗi xảy ra khi thực hiện lệnh!", ephemeral=True)
        except:
            await interaction.followup.send("Có lỗi xảy ra khi thực hiện lệnh!", ephemeral=True)

if __name__ == "__main__":
    if not token:
        print("❌ ERROR: DISCORD_TOKEN không được tìm thấy trong file .env!")
    else:
        print("🚀 Đang khởi động bot...")
        try:
            bot.run(token, log_handler=None, log_level=logging.WARNING)
        except Exception as e:
            print(f"❌ Lỗi khi chạy bot: {e}")