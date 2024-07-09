import os
import json
import discord
from discord.ext import commands
from discord import app_commands
import smtplib
from email.mime.text import MIMEText
import requests

config_file = 'config.json'
with open(config_file, 'r') as f:
    config = json.load(f)

EMAIL_ACCOUNTS = config['emailAccounts']
TOKEN = config['discordToken']
ROLE_ID1 = config['roleID1']
ROLE_ID2 = config['roleID2']
CHANNEL_ID = config['channelID']
LOG_CHANNEL_ID = config['logChannelID']
ALLOWED_USERNAME = config['allowedUsername']
ENTOMA_ID = config['entomaID']  # Entoma's Discord user ID

NOTIFICATION_CHANNEL_NAME = "Spammer Updates"

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.accepted_tos = set()
        self.notification_channel_id = config.get('notificationChannelID')

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        await self.change_presence(activity=discord.Game(name="Made By TeamMonster, Entoma & Xoid | https://discord.gg/YbjCe7fVdJ"))

        # Syncing commands with Discord
        await self.tree.sync()

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        member = ctx.author
        if member.id not in self.accepted_tos:
            await ctx.reply("Error: 948. Read ToS. `/tos`")
            return

    async def send_tos(self, member):
        embed = discord.Embed(
            title="Terms of Service",
            description="Please accept our terms of service to continue using the bot."
        )
        embed.add_field(
            name="TOS Link:",
            value="[Terms of Service](https://free-4665252.webadorsite.com/terms-of-service)"
        )
        view = discord.ui.View()
        accept_button = discord.ui.Button(label="Accept", style=discord.ButtonStyle.green)
        decline_button = discord.ui.Button(label="Decline", style=discord.ButtonStyle.red)

        async def accept_callback(interaction):
            self.accepted_tos.add(member.id)
            await interaction.response.send_message(
                "You have accepted the Terms of Service!", ephemeral=True)

        accept_button.callback = accept_callback

        async def decline_callback(interaction):
            await member.kick(reason="Declined Terms of Service")
            await interaction.response.send_message(
                "You have declined the Terms of Service. You have been kicked from the server.",
                ephemeral=True)

        decline_button.callback = decline_callback

        view.add_item(accept_button)
        view.add_item(decline_button)

        await member.send(embed=embed, view=view)

    async def ensure_notification_channel(self, guild_id):
        guild = self.get_guild(guild_id)
        if guild:
            existing_channel = discord.utils.get(guild.channels, name=NOTIFICATION_CHANNEL_NAME)
            if existing_channel:
                self.notification_channel_id = existing_channel.id
                config['notificationChannelID'] = existing_channel.id
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)
            else:
                self.notification_channel_id = None
                config['notificationChannelID'] = None
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)

bot = MyBot()

@bot.tree.command(name="tos", description="View and accept the Terms of Service")
async def tos(interaction: discord.Interaction):
    member = interaction.user
    await bot.send_tos(member)
    await interaction.response.send_message(
        "Please check your DMs for the Terms of Service.", ephemeral=True)

@bot.tree.command(name="webhook", description="Spam a webhook with a message and image")
async def webhook(interaction: discord.Interaction, webhook_url: str, msg: str, amount: int, image_url: str = None):
    if interaction.channel.id != CHANNEL_ID:
        await interaction.response.send_message(
            "This command can only be used in the Webhook Spam channel.",
            ephemeral=True)
        return

    member = interaction.user
    if member is None:
        await interaction.response.send_message("Member not found.",
                                                ephemeral=True)
        return

    await interaction.response.send_message(
        "Spamming the webhook... Please wait!", ephemeral=True)

    for _ in range(amount):
        try:
            response = requests.post(webhook_url, json={"content": msg})
            if response.status_code == 204:
                print(f"Webhook message sent successfully to {webhook_url}")
            else:
                print(f"Webhook message failed to send: {response.status_code}")
        except Exception as e:
            print(f"Error sending webhook message: {e}")

    await interaction.followup.send(
        f"Webhook spam completed. {amount} messages sent.")

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    log_embed = discord.Embed(title="Webhook Spam Log",
                              color=discord.Color.blue())
    log_embed.add_field(name="Webhook URL", value=webhook_url, inline=False)
    log_embed.add_field(name="Message", value=msg, inline=False)
    log_embed.add_field(name="User", value=interaction.user.name, inline=False)
    if image_url:
        log_embed.add_field(name="Image URL", value=image_url, inline=False)
    log_embed.set_footer(text=f"Spammed by: {interaction.user}")
    await log_channel.send(embed=log_embed)

@bot.tree.command(name="email", description="Spam an email address with a custom message")
async def email(interaction: discord.Interaction, to_address: str, message: str):
    if interaction.channel.id != CHANNEL_ID:
        await interaction.response.send_message(
            "This command can only be used in the Email Spam channel.",
            ephemeral=True)
        return

    member = interaction.user
    if member is None:
        await interaction.response.send_message("Member not found.",
                                                ephemeral=True)
        return

    required_role = None
    if ROLE_ID1 in [role.id for role in member.roles]:
        required_role = ROLE_ID1
        email_count = 10
    elif ROLE_ID2 in [role.id for role in member.roles]:
        required_role = ROLE_ID2
        email_count = 35
    else:
        await interaction.response.send_message(
            "You don't have the required role to use this command.",
            ephemeral=True)
        return

    await interaction.response.send_message(
        "Spamming the email... Please wait!", ephemeral=True)

    current_account = None
    for account in EMAIL_ACCOUNTS:
        if account['attempts'] < account['maxAttempts']:
            current_account = account
            break

    if current_account is None:
        await interaction.followup.send("All email accounts have reached their maximum attempts.",
                                        ephemeral=True)
        return

    for _ in range(email_count):
        try:
            msg = MIMEText(message)
            msg['Subject'] = 'Spam Email'
            msg['From'] = current_account['address']
            msg['To'] = to_address

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(current_account['address'], current_account['password'])
                server.sendmail(current_account['address'], to_address, msg.as_string())

            current_account['attempts'] += 1

        except Exception as e:
            await interaction.followup.send(f"Error sending email: {e}", ephemeral=True)
            return

    await interaction.followup.send(f"Email spam completed. {email_count} emails sent to {to_address}.",
                                    ephemeral=True)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    log_embed = discord.Embed(title="Email Spam Log",
                              color=discord.Color.blue())
    log_embed.add_field(name="To Address", value=to_address, inline=False)
    log_embed.add_field(name="Message", value=message, inline=False)
    log_embed.add_field(name="User", value=interaction.user.name, inline=False)
    log_embed.set_footer(text=f"Spammed by: {interaction.user}")
    await log_channel.send(embed=log_embed)

@bot.tree.command(name="notify", description="Send a notification message to the configured channel")
async def notify(interaction: discord.Interaction, *, msg: str):
    if interaction.user.name != ALLOWED_USERNAME:
        await interaction.response.send_message(
            "You are not allowed to use this command.", ephemeral=True)
        return

    notification_channel = bot.get_channel(bot.notification_channel_id)
    if notification_channel:
        await notification_channel.send(msg)
        await interaction.response.send_message(
            f"Notification sent to {notification_channel.mention}.", ephemeral=True)
    else:
        await interaction.response.send_message(
            "Notification channel not found. Please set it up using /set-notify-channel.", ephemeral=True)

@bot.tree.command(name="set-notify-channel", description="Set the notification channel for the /notify command")
async def set_notify_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.user.id != int(ENTOMA_ID):
        await interaction.response.send_message(
            "Only Entoma_ can use this command.", ephemeral=True)
        return

    bot.notification_channel_id = channel.id
    config['notificationChannelID'] = channel.id
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)
    await interaction.response.send_message(
        f"Notification channel set to {channel.mention}.", ephemeral=True)

bot.run(TOKEN)
