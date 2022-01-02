"""A Discord bot for structuring Discord debates"""
import asyncio
import discord
from discord.ext.commands import has_permissions, bot_has_permissions, converter, check, has_role
import db
from config import Config

BOT = discord.ext.commands.Bot(command_prefix='d!')


def does_not_have_role(name):
    def predicate(ctx):
        if not isinstance(ctx.channel, discord.abc.GuildChannel):
            return False

        role = discord.utils.get(ctx.author.roles, name=name)
        return role is None
    return check(predicate)


@bot_has_permissions(manage_channels=True, manage_roles=True)
@has_permissions(manage_channels=True)
@BOT.command()
async def create(ctx, name: converter.clean_content(), side1: converter.clean_content(), side2: converter.clean_content()):
    """Sets up a debate"""
    await ctx.send("I need help making an important decision. Send me your thoughts here: https://forms.gle/VQhtCBkVfwxGZDPK7")
    name = name.strip().replace('\r', '').replace('\n', '')
    side1 = side1.strip().replace('\r', '').replace('\n', '')
    side2 = side2.strip().replace('\r', '').replace('\n', '')
    if len(name) > 30:
        await ctx.send("Debate name is too long!")
        return
    if len("{}-{}".format(name, side1)) > 32 or len("{}-{}".format(name, side2)) > 32:
        await ctx.send("Please shorten the names, they are too long! Max combined length of debate name and sides "
                       "is 31 characters")
        return
    if side1 == side2:
        await ctx.send("Side names cannot be the same!")
        return
    blacklist_role = discord.utils.get(ctx.guild.roles, name='debatebot-blacklist')
    if blacklist_role is None:
        await ctx.guild.create_role(name='debatebot-blacklist')
    with db.Session() as session:
        already_debate = session.query(Storage).filter_by(guild=ctx.guild.id).one_or_none()
        if already_debate is not None:
            await ctx.send("There is already a debate in this server! Multiple debates are not supported at this time.")
            return
        side1_role = await ctx.guild.create_role(name=side1)

        side2_role = await ctx.guild.create_role(name=side2)

        cat = await ctx.guild.create_category_channel(name)
        await cat.set_permissions(target=ctx.guild.me, read_messages=True)
        await cat.set_permissions(target=ctx.guild.default_role, send_messages=False)

        main_channel = await ctx.guild.create_text_channel('{}-main'.format(name), category=cat)
        await main_channel.set_permissions(target=side1_role, send_messages=True)

        side1_channel = await ctx.guild.create_text_channel('{}-{}'.format(name, side1), category=cat)
        await side1_channel.set_permissions(target=ctx.guild.default_role, read_messages=False)
        await side1_channel.set_permissions(target=side1_role, read_messages=True, send_messages=True)

        side2_channel = await ctx.guild.create_text_channel('{}-{}'.format(name, side2), category=cat)
        await side2_channel.set_permissions(target=ctx.guild.default_role, read_messages=False)
        await side2_channel.set_permissions(target=side2_role, read_messages=True, send_messages=True)

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

    await ctx.send("Debate {} with sides {} and {} created successfully".format(name, side1, side2))
    await ctx.send("Side {} has the floor".format(side1))


@bot_has_permissions(manage_roles=True)
@bot_has_permissions(manage_roles=True)
@BOT.command()
async def floor(ctx, *, side):
    """Gives the floor to one side"""
    await ctx.send("I need help making an important decision. Send me your thoughts here: https://forms.gle/VQhtCBkVfwxGZDPK7")
    with db.Session() as session:
        is_admin = session.query(Storage).filter_by(admin=ctx.author.id, guild=ctx.guild.id).one_or_none()
        if is_admin is None:
            await ctx.send("You are not the facilitator!")
            return
        side1 = session.query(Storage).filter_by(side1_name=side, guild=ctx.guild.id).one_or_none()
        side2 = session.query(Storage).filter_by(side2_name=side, guild=ctx.guild.id).one_or_none()
        if side1 is not None:
            channel = ctx.guild.get_channel(channel_id=side1.main_channel)
            role1 = discord.utils.get(ctx.guild.roles, id=side1.side1_role)
            role2 = discord.utils.get(ctx.guild.roles, id=side1.side2_role)
            await channel.set_permissions(target=role1, send_messages=True)
            await channel.set_permissions(target=role2, send_messages=False)
            await ctx.send("Side {} has the floor".format(side))
        elif side2 is not None:
            channel = ctx.guild.get_channel(channel_id=side2.main_channel)
            role1 = discord.utils.get(ctx.guild.roles, id=side2.side1_role)
            role2 = discord.utils.get(ctx.guild.roles, id=side2.side2_role)
            await channel.set_permissions(target=role1, send_messages=False)
            await channel.set_permissions(target=role2, send_messages=True)
            await ctx.send("Side {} has the floor".format(side))
        else:
            await ctx.send("No side with that found! Please try again!")

locks = {}


@does_not_have_role(name='debatebot-blacklist')
@BOT.command()
async def join(ctx, *, side):
    """Lets a user join a side"""
    lock = locks.get(ctx.guild.id)
    if lock is None:
        lock = locks[ctx.guild.id] = asyncio.Lock()
    async with lock:
        with db.Session() as session:
            side1 = session.query(Storage).filter_by(side1_name=side, guild=ctx.guild.id).one_or_none()
            side2 = session.query(Storage).filter_by(side2_name=side, guild=ctx.guild.id).one_or_none()
            if side1 is not None:
                role = side1.side1_role
                existingroles = []
                for i in ctx.author.roles:
                    existingroles.append(i.id)
                if side1.side2_role in existingroles:
                    roletoremove = discord.utils.get(ctx.guild.roles, id=side1.side2_role)
                    await ctx.author.remove_roles(roletoremove)
            elif side2 is not None:
                role = side2.side2_role
                existingroles = []
                for i in ctx.author.roles:
                    existingroles.append(i.id)
                if side2.side1_role in existingroles:
                    roletoremove = discord.utils.get(ctx.guild.roles, id=side2.side1_role)
                    await ctx.author.remove_roles(roletoremove)
            else:
                await ctx.send("Invalid side to join!")
                return
            actual_role = discord.utils.get(ctx.guild.roles, id=role)
            await ctx.author.add_roles(actual_role)
            await ctx.send("Successfully joined you to {} side!".format(side))


@bot_has_permissions(manage_roles=True)
@BOT.command()
async def leave(ctx):
    """Removes a user from a particular side"""
    with db.Session() as session:
        active_debate = session.query(Storage).filter_by(guild=ctx.guild.id).one_or_none()
        role1 = discord.utils.get(ctx.guild.roles, id=active_debate.side1_role)
        role2 = discord.utils.get(ctx.guild.roles, id=active_debate.side2_role)
        sideroles = [role1, role2]
        for role in ctx.author.roles:
            if role in sideroles:
                await ctx.author.remove_roles(role)
        await ctx.send("{} has left".format(ctx.author.mention))


@bot_has_permissions(manage_channels=True, manage_roles=True)
@BOT.command()
async def end(ctx):
    """Ends a debate"""
    await ctx.send("I need help making an important decision. Send me your thoughts here: https://forms.gle/VQhtCBkVfwxGZDPK7")
    with db.Session() as session:
        active_debate = session.query(Storage).filter_by(guild=ctx.guild.id).one_or_none()
        if active_debate is None:
            await ctx.send("No active debate found for this guild!")
            return
        elif active_debate.admin != ctx.author.id:
            await ctx.send("You are not the admin, you don't have permission to do this!")
            return
        else:
            main_channel = ctx.guild.get_channel(active_debate.main_channel)
            cat_channel = main_channel.category
            role1 = discord.utils.get(ctx.guild.roles, id=active_debate.side1_role)
            role2 = discord.utils.get(ctx.guild.roles, id=active_debate.side2_role)
            for i in [role1, role2]:
                overwrite = cat_channel.overwrites_for(i)
                main_overwrite = main_channel.overwrites_for(i)
                if overwrite is not None:
                    overwrite.update(send_messages=False)
                    await cat_channel.set_permissions(target=i, overwrite=overwrite)
                if main_overwrite is not None:
                    await main_channel.set_permissions(target=i, overwrite=None)
            session.delete(active_debate)
            await ctx.send("Debate ended successfully!")


@BOT.command()
async def feedback(ctx):
    """Links to the feedback form"""
    await ctx.send("I need to make an important decision. Please help me here: https://forms.gle/VQhtCBkVfwxGZDPK7")


@BOT.command()
async def github(ctx):
    """Links to source code"""
    await ctx.send("Check out my bot code! You can see it here: https://github.com/tweirtx/DebateBot")


@BOT.event
async def on_ready():
    """Tells the host that it's ready"""
    print("Ready!")
    activity = discord.Activity(name="debates in {} guilds".format(len(BOT.guilds)), type=discord.ActivityType.watching)
    await BOT.change_presence(activity=activity)


@BOT.event
async def on_command_error(ctx, exception):
    await ctx.send(exception)
    print(exception)


@BOT.event
async def on_message(message):
    if message.author.bot:
        return
    await BOT.process_commands(message)


class Storage(db.DatabaseObject):
    """Stores everything"""
    __tablename__ = 'debateStorage'
    guild = db.Column(db.BigInteger, primary_key=True)
    side1_role = db.Column(db.BigInteger)
    side2_role = db.Column(db.BigInteger)
    main_channel = db.Column(db.BigInteger)
    side1_channel = db.Column(db.BigInteger)
    side2_channel = db.Column(db.BigInteger)
    side1_name = db.Column(db.String)
    side2_name = db.Column(db.String)
    admin = db.Column(db.BigInteger)


db.DatabaseObject.metadata.create_all()

BOT.run(Config.CONFIG['discord_token'])
