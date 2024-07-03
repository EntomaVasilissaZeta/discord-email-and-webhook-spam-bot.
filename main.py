# CREATED BY TeamMonster, entoma, And Xoid.
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import requests

load_dotenv()
EMAIL_ACCOUNTS = [
    {
        'address': os.getenv('SMTP_EMAIL1'),
        'password': os.getenv('SMTP_PASSWORD1'),
        'attempts': 0,
        'max_attempts': 30
    },
    {
        'address': os.getenv('SMTP_EMAIL2'),
        'password': os.getenv('SMTP_PASSWORD2'),
        'attempts': 0,
        'max_attempts': 30
    },
]

TOKEN = os.getenv('DISCORD_TOKEN')
ROLE_ID1 = int(os.getenv('ROLE_ID1')) # Regular user role
ROLE_ID2 = int(os.getenv('ROLE_ID2'))  # Paid user role
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
EMBED_ROLE_ID = int(os.getenv('EMBED_ROLE_ID'))  # Role that can use embeds. (coming soon.)

intents = discord.Intents.default()
intents.message_content = True


class MyBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.accepted_tos = set()  # Store users who have accepted the TOS

    async def setup_hook(self):
        guild = discord.Object(id=1166815592028848289)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    # This function will be called when a user runs a command
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        member = ctx.author
        if member.id not in self.accepted_tos:
            await ctx.reply("Error: 948. Read ToS. `/tos`")
            return
        # ... (Your existing command error handling) ...


# Function to send the TOS message with buttons

    async def send_tos(self, member):
        embed = discord.Embed(
            title="Terms of Service",
            description=
            "Please accept our terms of service to continue using the bot.")
        embed.add_field(
            name="TOS Link:",
            value=
            "[Terms of Service](https://free-4665252.webadorsite.com/terms-of-service)"
        )
        view = discord.ui.View()
        accept_button = discord.ui.Button(label="Accept",
                                          style=discord.ButtonStyle.green)
        decline_button = discord.ui.Button(label="Decline",
                                           style=discord.ButtonStyle.red)

        # Attach button actions
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

bot = MyBot()


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name="Watching: Made By TeamMonster & Xoid. | https://discord.gg/YbjCe7fVdJ"))

@bot.tree.command(name="tos",
                  description="View and accept the Terms of Service",
                  guild=discord.Object(id=1166815592028848289))
async def tos(interaction: discord.Interaction):
    member = interaction.user
    await bot.send_tos(member)
    await interaction.response.send_message(
        "Please check your DMs for the Terms of Service.")


@bot.tree.command(name="webhook",
                  description="Spam a webhook with a message and image",
                  guild=discord.Object(id=1166815592028848289))
async def webhook(interaction: discord.Interaction,
                  webhook_url: str,
                  msg: str,
                  amount: int,
                  image_url: str = None):
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
        if EMBED_ROLE_ID in [role.id for role in member.roles]:
            # User with EMBED_ROLE_ID can use embeds
            embed = discord.Embed(title="Webhook Spam",
                                  description=msg,
                                  color=discord.Color.blue())
            if image_url:
                embed.set_image(url=image_url)
            embed.set_footer(text="Powered by TeamMonster & Xoid")
            data = {"embeds": [embed.to_dict()]}
        else:
            # Regular user - plain text
            data = {"content": f"{msg}"}
            if image_url:
                data["content"] += f"\n{image_url}"

        try:
            response = requests.post(webhook_url, json=data)
            if response.status_code == 204:
                print(f"Webhook message sent successfully to {webhook_url}")
            else:
                print(
                    f"Webhook message failed to send: {response.status_code}")
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


@bot.tree.command(name="email",
                  description="Spam an email address with a custom message",
                  guild=discord.Object(id=1166815592028848289))
async def email(interaction: discord.Interaction, to_address: str,
                message: str):
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
        if account['attempts'] < account['max_attempts']:
            current_account = account
            break

    if current_account is None:
        await interaction.followup.send(
            "All email accounts have reached their maximum attempts. Cannot send emails.",
            ephemeral=True)
        return

    from_address = current_account['address']
    full_message = f"{message}\n\nPowered By TeamMonster & Xoid | https://discord.gg/yNhgks4j"

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtpserver:
            smtpserver.ehlo()
            smtpserver.starttls()
            smtpserver.ehlo()
            smtpserver.login(from_address, current_account['password'])
            for i in range(email_count):
                smtpserver.sendmail(from_address, to_address, full_message)
                print(
                    f'Email {i + 1} sent to {to_address} from {from_address}')
                current_account['attempts'] += 1

        embed = discord.Embed(
            title="Email Sent",
            description=
            f"{email_count} emails have been successfully sent to {to_address}.",
            color=discord.Color.green())
        embed.set_footer(text="Powered By TeamMonster & Xoid")
        success_message = await interaction.followup.send(embed=embed)
        await success_message.delete(delay=10)

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        log_embed = discord.Embed(title="Email Spam Log",
                                  color=discord.Color.blue())
        log_embed.add_field(name="Recipient", value=to_address, inline=False)
        log_embed.add_field(name="Message", value=message, inline=False)
        log_embed.add_field(name="User",
                            value=interaction.user.name,
                            inline=False)
        log_embed.set_footer(text=f"Sent from: {from_address}")
        await log_channel.send(embed=log_embed)

    except Exception as e:
        embed = discord.Embed(title="Email Sending Failed",
                              description=f"Failed to send email: {e}",
                              color=discord.Color.red())
        embed.set_footer(text="Powered By TeamMonster & Xoid")
        await interaction.followup.send(embed=embed)


bot.run(TOKEN)

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/send_email', methods=['POST'])
def send_email():
    data = request.json
    to_address = data.get('to_address')
    message = data.get('message')

    current_account = None
    for account in EMAIL_ACCOUNTS:
        if account['attempts'] < account['max_attempts']:
            current_account = account
            break

    if current_account is None:
        return jsonify({
            "status":
            "error",
            "message":
            "All email accounts have reached their maximum attempts."
        }), 500

    from_address = current_account['address']
    full_message = f"{message}\n\nPowered By TeamMonster & Xoid | https://discord.gg/yNhgks4j"

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtpserver:
            smtpserver.ehlo()
            smtpserver.starttls()
            smtpserver.ehlo()
            smtpserver.login(from_address, current_account['password'])
            smtpserver.sendmail(from_address, to_address, full_message)
            current_account['attempts'] += 1
            print(f'Email sent to {to_address} from {from_address}')
        return jsonify({
            "status": "success",
            "message": "Email sent successfully."
        }), 200  # Success status code
    except Exception as e:
        print(f"Failed to send email: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500  # Error status code

# Add the status 
app.route('/status', methods=['GET'])
def status():
  return "Watching: Made By TeamMonster & Xoid. | https://discord.gg/YbjCe7fVdJ"
