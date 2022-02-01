# Future
Hello,

As I'm sure you have heard, Discord is changing the requirements for bots on the platform. The way the bot currently works, using messages with the d! prefix, will not be supported in a few months.

I reached out to the community of users of the bot. I had to make the choice of whether or not to port the code to a new library and use slash commands. Out of thousands of users, 3 responded. To those 3, I am very grateful. However, these statistics have shown me that there is not sufficient interest to continue developing this.

I have removed the ability to add the bot to new servers. The bot will stop functioning completely on April 30, 2022, when Discord kills off message access to my and thousands of others' bots.

This project has grown larger than I ever thought it would have, and I'm grateful for every user I've helped. Thank you all.

Sincerely,

Travis Weir

# debatebot
This was a Discord bot that runs structured debates. 

Required permissions: manage roles, manage channels

Credits:

@tweirtx: Main bot dev and host

@octocynth: Testing this and making it actually good

When you run d!create (name) (side1) (side2), lots of things happen. First, a category channel is created. Next, channels for discussion and each side are created. Finally, roles are created, and the debate begins. Participants join sides and the facilitator gives each side the "floor" in the main channel at a time.
