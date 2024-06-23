import discord
import toml
from discord.ext import commands
from utils.commands import available_subcommands
from utils.pagination import paginated_embed_menus, PaginationView

class Helpermessage(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data = toml.load('config.toml')
        self.subjects = self.data['subjects']
        self.helpermessages = self.data['helpermessages']
        self.subject_channels = self.subjects.keys()
        self.helper_roles = [self.subjects[channel] for channel in self.subject_channels]

    @commands.hybrid_group()
    async def helpermessage(self, ctx: commands.Context):
        """
        Commands for handling reminders.
        """
        await available_subcommands(ctx)

    @helpermessage.command()
    async def list(self, ctx: commands.Context):
        """
        List all active helpermessage embeds
        """
        embed_dict = dict(
            title = 'List of all active helpermessages',
            description = f'Here is a list of all active helpermessages.',
        )
        names = [f'<#{channel}>' for channel in self.helpermessages.keys()]
        values = [f'https://discord.com/channels/{ctx.guild.id}/{channel}/{int(self.helpermessages[channel])}' for channel in self.helpermessages.keys()]
        embeds = paginated_embed_menus(names, values, embed_dict=embed_dict)
        embed, view = await PaginationView(ctx, embeds).return_paginated_embed_view()
        await ctx.send(embed=embed, view=view)

    async def embed_getter(self, edited_roles):
        for role in edited_roles:
            for channel, roles in self.subjects.items():
                if isinstance(role, list):
                    if role.id in roles:
                        discord_channel = await self.bot.fetch_channel(int(channel))
                        helpermessage = await discord_channel.fetch_message(int(self.helpermessages[channel]))
                        embed = helpermessage.embeds[0]
                        return helpermessage, role, embed
                elif role.id == roles:
                        discord_channel = await self.bot.fetch_channel(int(channel))
                        helpermessage = await discord_channel.fetch_message(int(self.helpermessages[channel]))
                        embed = helpermessage.embeds[0]
                        return helpermessage, role, embed
        return None, None, None

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Update helper message based on user helper/dehelper.
        """
        # checking if there has been a change in roles
        if before.roles != after.roles: 
            before_roles = set(before.roles)
            after_roles = set(after.roles)
            # checking whether roles were removed or added
            added_roles = after_roles - before_roles
            removed_roles = before_roles - after_roles
            # routine that runs to add the role
            if added_roles:
                helpermessage, role, embed = await self.embed_getter(added_roles)
                if helpermessage and role and embed:
                    new_embed = discord.Embed(description=embed.description)
                    for field in embed.fields:
                        if field.name == f'**{role.name}**':
                            new_embed.add_field(name=field.name, value=field.value + f'\n{after.mention}')
                        else:
                            new_embed.add_field(name=field.name, value=field.value)
                    await helpermessage.edit(embed=new_embed)

            # routine that runs to remove roles
            if removed_roles:
                helpermessage, role, embed = await self.embed_getter(removed_roles)
                if helpermessage and role and embed:
                    new_embed = discord.Embed(description=embed.description)
                    for field in embed.fields:
                        if field.name == f'**{role.name}**':
                            members = field.value.split('\n')
                            new_member_list = [member for member in members if member != after.mention]
                            new_embed.add_field(name=field.name, value='\n'.join(new_member_list))
                        else:
                            new_embed.add_field(name=field.name, value=field.value)
                    await helpermessage.edit(embed=new_embed)

    @helpermessage.command()
    async def create(self, ctx: commands.Context, channel: discord.TextChannel, helper_roles: commands.Greedy[discord.Role]):
        """
        Create the helpermessage embed for a specific channel given the channel and helper role
        """
        # Create the embed that will be pinned in the message
        description = f"***What are 'subject helpers'?*** \n\n Subject helpers, or simply \"helpers\", are members who volunteer their time and expertise to help fellow members with certain subjects. You can contact the Helpers for this subject by tagging the respective Helper role. Please wait 15 minutes after your question is posted before doing so, though. Most channels & helpers are fairly active anyway, so you should see your question(s) answered before then, whether by a helper or someone else.\n\n***How do I become a Helper?***\nTo apply to become a Helper, please fill out this form: <https://cutt.ly/ibo-subject-helper-form>\n\nYour application will be reviewed by the Helper Managers. Once a decision's been made, you'll be notified via DMs. \n\n **Subject helpers for {channel.name}:**"
        helper_embed = discord.Embed(description=description)
        # add the field displaying the helpers
        for role in helper_roles:
            subject_helpers = [member.mention for member in ctx.guild.members if role in member.roles]
            helper_embed.add_field(
                name=f"**{role.name}**",
                value="\n".join(subject_helpers),
                inline=False
            )
        # send the message
        helpermessage = await channel.send(embed=helper_embed)
        # pin the message
        await helpermessage.pin()
        # save the message id of the helpermessage to the helpermessages section
        # of the config.toml file
        self.helpermessages[str(channel.id)] = helpermessage.id
        with open('config.toml', 'w') as file:
            toml.dump(self.data, file)

    @helpermessage.command()
    async def delete(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Delete the helpermessage embed for a specific channel given the channel and helper role
        """
        try:
            helpermessage = int(self.helpermessages[str(channel.id)])
        except KeyError:
            await ctx.send("That helpermessage does not exist")

    @helpermessage.command()
    async def edit(self, ctx: commands.Context, *, content: str):
        """
        Edit the content in the helpermessage
        """
        for channel in self.helpermessages:
            discord_channel = await self.bot.fetch_channel(channel)
            helpermessage = await discord_channel.fetch_message(int(self.helpermessages[channel]))
            embed = helpermessage.embeds[0]
            embed.description = content
            await helpermessage.edit(embed=embed)
        await ctx.send("Updated messages successfully")



async def setup(bot: commands.Bot):
    await bot.add_cog(Helpermessage(bot))
