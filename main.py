import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

# Intent
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  

bot = commands.Bot(command_prefix="/", intents=intents)

# data cash
role_panels = {}

@bot.event
async def on_ready():
    print(f"Bot起動完了: {bot.user}")
    try:
        synced_commands = await bot.tree.sync()
        print(f"Slashコマンドを {len(synced_commands)} 件同期しました。")
    except Exception as e:
        print(f"Slashコマンドの同期中にエラー: {e}")

# /rp_create
@bot.tree.command(name="rp_create", description="リアクションロール用のパネルを作成します")
async def rp_create(interaction: discord.Interaction):
    embed = discord.Embed(
        title="役職パネル",
        description="以下の絵文字をクリックするとロールがトグルされます。"
    )
    panel_msg = await interaction.channel.send(embed=embed)
    role_panels[panel_msg.id] = {}  
    await interaction.response.send_message(
        f"役職パネルを作成しました！ (message_id: {panel_msg.id})",
        ephemeral=True
    )

# /rp_add 
@bot.tree.command(name="rp_add", description="既存の役職パネルに役職と絵文字を追加します")
@app_commands.describe(
    message_id="先ほど作成したパネルのメッセージID",
    role="付与したい役職",
    emoji="反応に使う絵文字 (例: ✅ や <:skull> など)"
)
async def rp_add(interaction: discord.Interaction, message_id: str, role: discord.Role, emoji: str):
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("メッセージIDが正しくありません。", ephemeral=True)
        return

    if msg_id not in role_panels:
        await interaction.response.send_message("指定されたパネルが見つかりません。", ephemeral=True)
        return

    role_panels[msg_id][emoji] = role.id

    channel = interaction.channel
    try:
        panel_msg = await channel.fetch_message(msg_id)
        await panel_msg.add_reaction(emoji)
    except discord.NotFound:
        await interaction.response.send_message("メッセージが見つかりませんでした。", ephemeral=True)
        return
    except discord.HTTPException:
        await interaction.response.send_message("絵文字の追加に失敗しました。", ephemeral=True)
        return


    embed = panel_msg.embeds[0] if panel_msg.embeds else discord.Embed(title="役職パネル")
    new_line = f"\n{emoji} → {role.mention}"
    if embed.description is None:
        embed.description = new_line.strip()
    else:
        embed.description += new_line
    await panel_msg.edit(embed=embed)

    await interaction.response.send_message(
        f"パネル (ID: {msg_id}) に {emoji} → {role.name} を追加しました。",
        ephemeral=True
    )


@bot.tree.command(name="rp_remove", description="役職パネルから指定した役職の選択を消します")
@app_commands.describe(
    role="消したい役職（例: @test）"
)
async def rp_remove(interaction: discord.Interaction, role: discord.Role):
    removed = False

    for msg_id, mapping in role_panels.items():
        to_remove = []
        for emoji, role_id in mapping.items():
            if role_id == role.id:
                to_remove.append(emoji)
        if to_remove:
            removed = True
            for emoji in to_remove:
                del mapping[emoji]
                # AAAAAAAAA
                channel = interaction.channel
                try:
                    panel_msg = await channel.fetch_message(msg_id)
                    await panel_msg.clear_reaction(emoji)
                    # rm
                    if panel_msg.embeds:
                        embed = panel_msg.embeds[0]
                        if embed.description:
                            # emoji
                            lines = embed.description.split("\n")
                            new_lines = [line for line in lines if emoji not in line or role.mention not in line]
                            embed.description = "\n".join(new_lines)
                            await panel_msg.edit(embed=embed)
                except Exception as e:
                    print(f"パネル (ID: {msg_id}) の更新に失敗しました: {e}")

    if removed:
        await interaction.response.send_message(
            f"役職パネルから {role.name} の選択を削除しました。",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "指定した役職はどのパネルにも登録されていませんでした。",
            ephemeral=True
        )

# toggle role
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    
    if payload.user_id == bot.user.id:
        return

    msg_id = payload.message_id
    emoji = str(payload.emoji)
    if msg_id not in role_panels:
        return
    if emoji not in role_panels[msg_id]:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    role_id = role_panels[msg_id][emoji]
    role = guild.get_role(role_id)
    if role is None:
        return

    member = await guild.fetch_member(payload.user_id)
    if member is None:
        return

    # add/remove
    if role in member.roles:
        await member.remove_roles(role, reason="リアクションによるロールトグル: 削除")
        print(f"{member.name} から {role.name} を削除しました。")
    else:
        await member.add_roles(role, reason="リアクションによるロールトグル: 付与")
        print(f"{member.name} に {role.name} を付与しました。")

    # emoji
    channel = bot.get_channel(payload.channel_id)
    if channel:
        try:
            message = await channel.fetch_message(msg_id)
            await message.remove_reaction(payload.emoji, member)
        except Exception as e:
            print(f"リアクションの削除に失敗: {e}")

if __name__ == "__main__":
    TOKEN = ""  # TOKEN XD
    asyncio.run(bot.start(TOKEN))
