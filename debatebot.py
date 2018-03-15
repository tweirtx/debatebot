import discord
import os
import json
from discord.ext.commands import Bot, has_permissions, bot_has_permissions
from . import db

config = {
	'discord_token': "Put Discord API Token here.",
}
config_file = 'config.json'

if os.path.isfile(config_file):
	with open(config_file) as f:
		config.update(json.load(f))

with open('config.json', 'w') as f:
	json.dump(config, f, indent='\t')


bot = discord.ext.commands.Bot(command_prefix='d!')


@bot_has_permissions(manage_channels=True, manage_roles=True)
@has_permissions(manage_channels=True)
@bot.command()
async def create(ctx, name, side1, side2):
	with db.Session() as session:
		already_debate = session.query(Storage).filter_by(guild=ctx.guild.id)
		if already_debate is not None:
			await ctx.send("There is already a debate in this server! Multiple debates are not supported at this time.")
			return
		await ctx.guild.create_role('{} - {}'.format(name, side1))
		side1_role = ctx.guild.get_role('{} - {}'.format(name, side1)).id

		await ctx.guild.create_role('{} - {}'.format(name, side2))
		side2_role = ctx.guild.get_role('{} - {}'.format(name, side2)).id

		await ctx.guild.create_category_channel(name)
		cat = ctx.guild.get_channel(name)
		cat.permissions(send_messages=False)

		await ctx.guild.create_channel('{} - Main'.format(name))
		main_channel = ctx.guild.get_channel('{} - Main'.format(name))
		main_channel.overwrites_for(side1_role).update(send_messages=True)

		await ctx.guild.create_channel('{} - {}'.format(name, side1), category=cat)
		side1_channel = ctx.guild.get_channel('{} - {}'.format(name, side1))
		side1_channel.permissions(read_messages=False)
		side1_channel.overwrites_for(side1_role).update(read_messages=True, send_messages=True)

		await ctx.guild.create_channel('{} - {}'.format(name, side2), category=cat)
		side2_channel = ctx.guild.get_channel('{} - {}'.format(name, side2))
		await side2_channel.permissions(read_messages=False)
		side2_channel.overwrites_for(side2_role).update(read_messages=True, send_messages=True)

		debate = Storage(guild=ctx.guild.id, side1_role=side1_role, side2_role=side2_role, main_channel=main_channel,
																			side1_channel=side1_channel,
																			side2_channel=side2_channel,
																			side1_name=side1,
																			side2_name=side2,
																			admin=ctx.author.id)
		session.add(debate)

	await ctx.send("Debate {} with sides {} and {} on the other created successfully".format(name, side1, side2))
	await ctx.send("Side {} has the floor".format(side1))


@bot_has_permissions(manage_roles=True)
@bot.command()
async def floor(ctx, side):
	with db.Session() as session:
		is_admin = session.query(Storage).filter_by(admin=ctx.author.id, guild=ctx.guild.id).one_or_none()
		if is_admin is None:
			await ctx.send("You are not the facilitator!")
			return
		side1 = session.query(Storage).filter_by(side1_name=side).one_or_none()
		side2 = session.query(Storage).filter_by(side2_name=side).one_or_none()
		if side1 is not None:
			overrides = ctx.channel.overwrites_for(side1.side1_role)
			overrides.update(send_messages=True)
			otheroverrides = ctx.channel.overwrites_for(side1.side2_role)
			otheroverrides.update(send_messages=False)
			print("Give the corresponding role ability to send messages and remove that from other")
		elif side2 is not None:
			overrides = ctx.channel.overwrites_for(side2.side2_role)
			overrides.update(send_messages=True)
			otheroverrides = ctx.channel.overwrites_for(side2.side1_role)
			otheroverrides.update(send_messages=False)
			print("Give the corresponding role ability to send messages and remove that from other")
		else:
			await ctx.send("No side with that found! Please try again!")


@bot.command()
async def join(ctx, side):
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


@bot.command()
async def end(ctx):
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
			cat_channel = bot.get_channel(active_debate.main_channel).category
			overwrite1 = cat_channel.overwrites_for(active_debate.side1_role)
			overwrite2 = cat_channel.overwrites_for(active_debate.side2_role)
			overwrites = [overwrite1, overwrite2]
			for i in overwrites:
				i.update(send_messages=False)
			session.delete(active_debate)
			await ctx.send("Debate ended successfully!")


@bot.command()
async def feedback(ctx):
	await ctx.send("Want to give feedback on the bot? Go here: <insert shortened form URL>")


@bot.command()
async def github(ctx):
	await ctx.send("Check out my bot code! You can see it here: https://github.com/tweirtx/DebateBot")


@bot.command()
async def help(ctx):
	await ctx.send("Need some help? Find the help guide at https://tweirtx.github.io/debatebot-help.html")


class Storage(db.DatabaseObject):
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


bot.run(config['discord_token'])
