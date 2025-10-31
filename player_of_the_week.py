import discord
import random
from ids import ccchannels, ccroles

async def give(guild: discord.Guild):

    await guild.get_channel(ccchannels.MOD_CHANNEL).send("Choosing new player of the week...")

    members = guild.members
    rand = random.randint(0, len(members))
    new_pow = members[rand]
    
    current_pow = guild.get_role(ccroles.POW).members[0]
    await current_pow.remove_roles(guild.get_role(ccroles.POW))

    await new_pow.add_roles(guild.get_role(ccroles.POW))
    announcement = f"{guild.default_role} {new_pow.mention} is now player of the week!"
    await guild.get_channel(ccchannels.ANNOUNCEMENTS).send(announcement)