import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import asyncio
import random

CONFIG_PATH = # replace with your path to where the json file should be 

def load_config(guild_id):
    path = f"{CONFIG_PATH}/{guild_id}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "vanity_string": None,
        "message_on": True,
        "message_text": "{user.mention} has the vanity in their status!",
        "role": None,
        "channel": None,
        "log_channel": None
    }

def save_config(guild_id, data):
    os.makedirs(CONFIG_PATH, exist_ok=True)
    path = f"{CONFIG_PATH}/{guild_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

class Vanity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_vanity.start()

    def cog_unload(self):
        self.check_vanity.cancel()

    # background loop
    @tasks.loop(seconds=2)
    async def check_vanity(self):
        for guild in self.bot.guilds:
            config = load_config(guild.id)
            vanity = config.get("vanity_string")
            if not vanity:
                continue
            for member in guild.members:
                if member.bot:
                    continue
                status = str(member.activity) if member.activity else ""
                has_vanity = vanity.lower() in status.lower()
                key = f"{guild.id}-{member.id}"
                if not hasattr(self, "tracked"):
                    self.tracked = {}
                prev = self.tracked.get(key, False)

                if has_vanity and not prev:
                    await self.handle_detect(member, config, True)
                elif not has_vanity and prev:
                    await self.handle_detect(member, config, False)

                self.tracked[key] = has_vanity

    async def handle_detect(self, member, config, detected):
        guild = member.guild

        # log channel
        log_channel_id = config.get("log_channel")
        if log_channel_id:
            log_channel = guild.get_channel(int(log_channel_id))
            if log_channel:
                state = "ON" if detected else "OFF"
                await log_channel.send(
                    f"[LOG] {member} ({member.id}) vanity {state}"
                )

        # give / remove role
        role_id = config.get("role")
        if role_id:
            role = guild.get_role(int(role_id))
            if role:
                try:
                    if detected:
                        await member.add_roles(role, reason="Vanity detected")
                    else:
                        await member.remove_roles(role, reason="Vanity removed")
                except discord.Forbidden:
                    pass

        # message channel
        if detected or config.get("message_on", True):
            channel_id = config.get("channel")
            if channel_id:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    msg = config.get("message_text", "{user.mention} vanity detected!")
                    await channel.send(msg.replace("{user.mention}", member.mention))

    # commands
    @app_commands.command(name="vanity_set", description="Set vanity string")
    async def vanity_set(self, interaction: discord.Interaction, string: str):
        config = load_config(interaction.guild.id)
        config["vanity_string"] = string
        save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"Vanity string set to `{string}`")

    @app_commands.command(name="vanity_message", description="Set vanity detection message")
    async def vanity_message(self, interaction: discord.Interaction, mode: str, *, message: str = None):
        config = load_config(interaction.guild.id)
        if mode.lower() in ["on", "off"]:
            config["message_on"] = (mode.lower() == "on")
        if message:
            config["message_text"] = message
        save_config(interaction.guild.id, config)
        await interaction.response.send_message("Vanity message updated.")

    @app_commands.command(name="vanity_role", description="Set vanity role")
    async def vanity_role(self, interaction: discord.Interaction, role: discord.Role):
        config = load_config(interaction.guild.id)
        config["role"] = str(role.id)
        save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"Vanity role set to {role.mention}")

    @app_commands.command(name="vanity_channel", description="Set vanity message channel")
    async def vanity_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_config(interaction.guild.id)
        config["channel"] = str(channel.id)
        save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"Vanity channel set to {channel.mention}")

    @app_commands.command(name="vanity_log", description="Set vanity log channel")
    async def vanity_log(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_config(interaction.guild.id)
        config["log_channel"] = str(channel.id)
        save_config(interaction.guild.id, config)
        await interaction.response.send_message(f"Vanity log channel set to {channel.mention}")

    @app_commands.command(name="vanity_test", description="Test vanity detection message")
    async def vanity_test(self, interaction: discord.Interaction):
        config = load_config(interaction.guild.id)
        msg = config.get("message_text", "{user.mention} vanity detected!")
        await interaction.response.send_message(msg.replace("{user.mention}", interaction.user.mention))

async def setup(bot):
    await bot.add_cog(Vanity(bot))
