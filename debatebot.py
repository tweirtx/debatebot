"""A Discord bot for structuring Discord debates"""
import os
import json
import discord
from discord.ext.commands import has_permissions, bot_has_permissions
import db


CONFIG = {
    'discord_token': "Put Discord API Token here.",
}
CONFIG_FILE = 'config.json'

if os.path.isfile(CONFIG_FILE):
    with open(CONFIG_FILE) as f:
        CONFIG.update(json.load(f))

with open('config.json', 'w') as f:
    json.dump(CONFIG, f, indent='\t')


BOT = discord.ext.commands.Bot(command_prefix='d!')


@bot_has_permissions(manage_channels=True, manage_roles=True)
@has_permissions(manage_channels=True)
@BOT.command()
async def create(ctx, name, side1, side2):
    """Sets up a debate"""
    with db.Session() as session:
        already_debate = session.query(Storage).filter_by(guild=ctx.guild.id).one_or_none()
        if already_debate is not None:
            await ctx.send("There is already a debate in this server! Multiple debates are not supported at this time.")
            return
        side1_role = await ctx.guild.create_role()
        await side1_role.edit(name='{}'.format(side1))

        side2_role = await ctx.guild.create_role()
        await side2_role.edit(name='{}'.format(side2))

        cat = await ctx.guild.create_category_channel(name)
        await cat.set_permissions(target=ctx.guild.default_role, send_messages=False)

        main_channel = await ctx.guild.create_text_channel('{}-main'.format(name), category=cat)
        main_channel.overwrites_for(side1_role).update(send_messages=True)

        side1_channel = await ctx.guild.create_text_channel('{}-{}'.format(name, side1), category=cat)
        await side1_channel.set_permissions(target=ctx.guild.default_role, read_messages=False)
        side1_channel.overwrites_for(side1_role).update(read_messages=True, send_messages=True)

        side2_channel = await ctx.guild.create_text_channel('{}-{}'.format(name, side2), category=cat)
        await side2_channel.set_permissions(target=ctx.guild.default_role, read_messages=False)
        side2_channel.overwrites_for(side2_role).update(read_messages=True, send_messages=True)

        debate = Storage(guild=ctx.guild.id,
                         side1_role=side1_role.id,
                         side2_role=side2_role.id,
                         main_channel=main_channel.id,
                         side1_channel=side1_channel.id,
                         side2_channel=side2_channel.id,
                         side1_name=side1,
                         side2_name=side2,
                         admin=ctx.author.id)
        session.add(debate)

    await ctx.send("Debate {} with sides {} and {} on the other created successfully".format(name, side1, side2))
    await ctx.send("Side {} has the floor".format(side1))


@bot_has_permissions(manage_roles=True)
@BOT.command()
async def floor(ctx, *, side):
    """Gives the floor to one side"""
    with db.Session() as session:
        is_admin = session.query(Storage).filter_by(admin=ctx.author.id, guild=ctx.guild.id).one_or_none()
        if is_admin is None:
            await ctx.send("You are not the facilitator!")
            return
        side1 = session.query(Storage).filter_by(side1_name=side).one_or_none()
        side2 = session.query(Storage).filter_by(side2_name=side).one_or_none()
        if side1 is not None:
            role1 = discord.utils.get(ctx.guild.roles, name="{}".format(side1.side1_name))
            role2 = discord.utils.get(ctx.guild.roles, name="{}".format(side1.side2_name))
            overrides = ctx.channel.overwrites_for(role1)
            overrides.update(send_messages=True)
            otheroverrides = ctx.channel.overwrites_for(role2)
            otheroverrides.update(send_messages=False)
            await ctx.send("Side {} has the floor".format(side))
        elif side2 is not None:
            role1 = discord.utils.get(ctx.guild.roles, name="{}".format(side2.side1_name))
            role2 = discord.utils.get(ctx.guild.roles, name="{}".format(side2.side2_name))
            overrides = ctx.channel.overwrites_for(role1)
            overrides.update(send_messages=False)
            otheroverrides = ctx.channel.overwrites_for(role2)
            otheroverrides.update(send_messages=True)
            await ctx.send("Side {} has the floor".format(side))
        else:
            await ctx.send("No side with that found! Please try again!")


@BOT.command()
async def join(ctx, side: discord.Role):
    """Lets a user join a side"""
    with db.Session() as session:
        side1 = session.query(Storage).filter_by(side1_name=side).one_or_none()
        side2 = session.query(Storage).filter_by(side2_name=side).one_or_none()
        if side1 is not None:
            role = side1.side1_role
            existingroles = ctx.author.roles
            if side1.side2_role in existingroles:
                ctx.author.remove_roles(side1.side2_role)
        elif side2 is not None:
            role = side2.side2_role
            existingroles = ctx.author.roles
            if side2.side1_role in existingroles:
                ctx.author.remove_roles(side2.side1_role)
        else:
            await ctx.send("Invalid side to join!")
            return
        ctx.author.add_roles(role)
        await ctx.send("Successfully joined you to {} side!".format(side))


@BOT.command()
async def end(ctx):
    """Ends a debate"""
    with db.Session() as session:
        active_debate = session.query(Storage).filter_by(guild=ctx.guild.id).one_or_none()
        if active_debate is None:
            await ctx.send("No active debate found for this guild!")
            return
        elif active_debate.admin != ctx.author.id:
            await ctx.send("You are not the admin, you don't have permission to do this!")
            return
        else:
            # discord.CategoryChannel(data=active_debate.channelcat, guild=ctx.guild, state=True)
            cat_channel = BOT.get_channel(active_debate.main_channel).category
            for i in ctx.guild.roles:
                if i.id == active_debate.side1_role:
                    role1 = i
                if i.id == active_debate.side2_role:
                    role2 = i
            overwrites = []
            try:
                overwrite1 = cat_channel.overwrites_for(role1)
                overwrites.append(overwrite1)
            except UnboundLocalError:
                await ctx.send("Not deleting nonexistent role for {}".format(active_debate.side1_name))
            try:
                overwrite2 = cat_channel.overwrites_for(role2)
                overwrites.append(overwrite2)
            except UnboundLocalError:
                await ctx.send("Not deleting nonexistent role for {}".format(active_debate.side2_name))
            for i in overwrites:
                i.update(send_messages=False)
            session.delete(active_debate)
            await ctx.send("Debate ended successfully!")


@BOT.command()
async def feedback(ctx):
    """Links to the feedback form"""
    await ctx.send("Want to give feedback on the bot? Go here: https://goo.gl/forms/EyEmiCbvKhA3Ngz22")


@BOT.command()
async def github(ctx):
    """Links to source code"""
    await ctx.send("Check out my bot code! You can see it here: https://github.com/tweirtx/DebateBot")


@BOT.event
async def on_ready():
    """Tells the host that it's ready"""
    print("Ready!")


class Storage(db.DatabaseObject):
    """Stores everything"""
    __tablename__ = 'debateStorage'
    guild = db.Column(db.Integer, primary_key=True)
    side1_role = db.Column(db.Integer)
    side2_role = db.Column(db.Integer)
    main_channel = db.Column(db.Integer)
    side1_channel = db.Column(db.Integer)
    side2_channel = db.Column(db.Integer)
    side1_name = db.Column(db.String)
    side2_name = db.Column(db.String)
    admin = db.Column(db.Integer)


BOT.run(CONFIG['discord_token'])
