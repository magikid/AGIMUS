from common import *
from queries.badge_tags import *
from utils.badge_utils import *
from utils.check_channel_access import access_check

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def user_badges_autocomplete(ctx:discord.AutocompleteContext):
  user_badges = [b['badge_name'] for b in await db_get_user_badges(ctx.interaction.user.id)]
  if len(user_badges) == 0:
    user_badges = ["You don't have any badges yet!"]

  return [result for result in user_badges if ctx.value.lower() in result.lower()]


async def tags_autocomplete(ctx:discord.AutocompleteContext):
  user_tags = [t['tag_name'] for t in await db_get_user_badge_tags(ctx.interaction.user.id)]
  user_tags.sort()
  if len(user_tags) == 0:
    user_tags = ["You don't have any tags yet!"]

  return [t for t in user_tags if ctx.value.lower() in t.lower()]

# ____   ____.__
# \   \ /   /|__| ______  _  ________
#  \   Y   / |  |/ __ \ \/ \/ /  ___/
#   \     /  |  \  ___/\     /\___ \
#    \___/   |__|\___  >\/\_//____  >
#                    \/           \/
class TagSelector(discord.ui.Select):
  def __init__(self, user_badge_tags, associated_tags):
    associated_tag_ids = [t['id'] for t in associated_tags]
    options = [
      discord.SelectOption(
        label=t['tag_name'],
        value=str(t['id']),
        default=t['id'] in associated_tag_ids
      )
      for t in user_badge_tags
    ]

    super().__init__(
      placeholder="Select/Deselect Tags",
      min_values=0,
      max_values=len(user_badge_tags),
      options=options,
      row=1
    )

  async def callback(self, interaction:discord.Interaction):
    await interaction.response.defer()
    self.view.tag_ids = self.values


class TagButton(discord.ui.Button):
  def __init__(self, user_discord_id, badge_info):
    self.user_discord_id = user_discord_id
    self.badge_info = badge_info
    super().__init__(
      label="Tag Badge",
      style=discord.ButtonStyle.primary,
      row=2
    )

  async def callback(self, interaction:discord.Interaction):
    associated_tags = await db_get_associated_badge_tags(self.user_discord_id, self.badge_info['badge_filename'])
    tag_ids_to_delete = [t['id'] for t in associated_tags if t['id'] not in self.view.tag_ids]
    await db_delete_badge_tags_associations(tag_ids_to_delete, self.badge_info['badge_filename'])
    if len(self.view.tag_ids):
      await db_create_badge_tags_associations(self.user_discord_id, self.badge_info['badge_filename'], self.view.tag_ids)

    new_associated_tags = await db_get_associated_badge_tags(self.user_discord_id, self.badge_info['badge_filename'])
    new_associated_tag_names = [t['tag_name'] for t in new_associated_tags]

    if len(new_associated_tag_names):
      description = f"**{self.badge_info['badge_name']}** is now tagged with:" + "\n\n- " + "\n- ".join(new_associated_tag_names) + "\n\n" + "Use `/tags showcase` to show off your tags!"
    else:
      description = f"**{self.badge_info['badge_name']}** currently has no tags associated!"

    await interaction.response.edit_message(
      embed=discord.Embed(
        title="Tags Updated",
        description=description,
        color=discord.Color.green()
      ),
      view=None,
      files=[]
    )


class CarouselButton(discord.ui.Button):
  def __init__(self, user_discord_id, badge_info):
    self.user_discord_id = user_discord_id
    self.badge_info = badge_info
    super().__init__(
      label="Tag Badge / Move On",
      style=discord.ButtonStyle.primary,
      row=2
    )

  async def callback(self, interaction:discord.Interaction):
    await interaction.response.defer()
    associated_tags = await db_get_associated_badge_tags(self.user_discord_id, self.badge_info['badge_filename'])
    tag_ids_to_delete = [t['id'] for t in associated_tags if t['id'] not in self.view.tag_ids]
    await db_delete_badge_tags_associations(tag_ids_to_delete, self.badge_info['badge_filename'])
    if len(self.view.tag_ids):
      await db_create_badge_tags_associations(self.user_discord_id, self.badge_info['badge_filename'], self.view.tag_ids)

    new_associated_tags = await db_get_associated_badge_tags(self.user_discord_id, self.badge_info['badge_filename'])
    new_associated_tag_names = [t['tag_name'] for t in new_associated_tags]

    if len(new_associated_tag_names):
      description = f"**{self.badge_info['badge_name']}** is now tagged with:" + "\n\n- " + "\n- ".join(new_associated_tag_names) + "\n\n" + "Use `/tags showcase` to show off your tags!"
    else:
      description = f"**{self.badge_info['badge_name']}** currently has no tags associated!"

    summary_embed = discord.Embed(
        title="Tag Summary",
        description=description,
        color=discord.Color.green()
      )
    summary_badge_image = discord.File(fp=f"./images/badges/{self.badge_info['badge_filename']}", filename=self.badge_info['badge_filename'])
    summary_embed.set_image(url=f"attachment://{self.badge_info['badge_filename']}")
    await interaction.edit(
      embed=summary_embed,
      view=None,
      files=[summary_badge_image]
    )

    user_badges = await db_get_user_badges(self.user_discord_id)
    user_badge_filenames = [b['badge_filename'] for b in user_badges]
    previous_badge_filename = await db_get_last_carousel_tagged_badge_filename(self.user_discord_id)
    if previous_badge_filename:
      next_position = user_badge_filenames.index(previous_badge_filename) + 1
    else:
      next_position = 1

    if next_position > len(user_badges) - 1:
      await interaction.respond(
        embed=discord.Embed(
          title="You're done!",
          description="You've completed tagging every badge in your inventory! Nice.",
          color=discord.Color.blurple()
        ),
        ephemeral=True
      )
      await db_clear_last_carousel_tagged_badge_filename(self.user_discord_id)
      return

    next_badge = user_badges[next_position]
    await db_upsert_last_carousel_tagged_badge_filename(self.user_discord_id, next_badge['badge_filename'])

    new_view = await generateTagCarouselView(self.user_discord_id, next_badge)
    embed = discord.Embed(
      title=next_badge['badge_name'],
      color=discord.Color.dark_purple()
    )
    badge_image = discord.File(fp=f"./images/badges/{next_badge['badge_filename']}", filename=next_badge['badge_filename'])
    embed.set_image(url=f"attachment://{next_badge['badge_filename']}")

    await interaction.respond(embed=embed, file=badge_image, view=new_view, ephemeral=True)



class TagBadgeView(discord.ui.View):
  def __init__(self, user_discord_id, badge_info, user_badge_tags, associated_tags):
    super().__init__()
    self.tag_ids = []
    self.add_item(TagSelector(user_badge_tags, associated_tags))
    self.add_item(TagButton(user_discord_id, badge_info))

async def generateTagBadgeView(user_discord_id, badge_info):
  user_badge_tags = await db_get_user_badge_tags(user_discord_id)
  associated_tags = await db_get_associated_badge_tags(user_discord_id, badge_info['badge_filename'])

  return TagBadgeView(user_discord_id, badge_info, user_badge_tags, associated_tags)


class TagCarouselView(discord.ui.View):
  def __init__(self, user_discord_id, badge_info, user_badge_tags, associated_tags):
    super().__init__()
    self.user_discord_id = user_discord_id
    self.tag_ids = [str(t['id']) for t in associated_tags]

    self.add_item(TagSelector(user_badge_tags, associated_tags))
    self.add_item(CarouselButton(user_discord_id, badge_info))

async def generateTagCarouselView(user_discord_id, badge_info):
  user_badge_tags = await db_get_user_badge_tags(user_discord_id)
  associated_tags = await db_get_associated_badge_tags(user_discord_id, badge_info['badge_filename'])

  return TagCarouselView(user_discord_id, badge_info, user_badge_tags, associated_tags)


# __________             .___           ___________                    _________
# \______   \_____     __| _/ ____   ___\__    ___/____     ____  _____\_   ___ \  ____   ____
#  |    |  _/\__  \   / __ | / ___\_/ __ \|    |  \__  \   / ___\/  ___/    \  \/ /  _ \ / ___\
#  |    |   \ / __ \_/ /_/ |/ /_/  >  ___/|    |   / __ \_/ /_/  >___ \\     \___(  <_> ) /_/  >
#  |______  /(____  /\____ |\___  / \___  >____|  (____  /\___  /____  >\______  /\____/\___  /
#         \/      \/      \/_____/      \/             \//_____/     \/        \/      /_____/
class BadgeTags(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.max_tags = 25 # We can only have 25 items in a Discord select component

  tags_group = discord.SlashCommandGroup("tags", "Badge Tags Commands!")

  @tags_group.command(
    name="create",
    description="Create a new badge tag. (NOTE: You can have a max of 25 tags)"
  )
  @option(
    name="tag",
    description="Name of the tag to create",
    required=True,
    min_length=1,
    max_length=24
  )
  async def create(self, ctx:discord.ApplicationContext, tag:str):
    await ctx.defer(ephemeral=True)

    tag = tag.strip()
    if len(tag) == 0:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You Must Enter A Tag!",
          description=f"Tag name cannot be empty!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    current_user_tags = await db_get_user_badge_tags(ctx.author.id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    if tag in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Already Exists",
          description=f"You've already created **{tag}**!" + "\n\n" + "You can associate your badges with this tag via `/tags tag`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if len(current_user_tags) >= self.max_tags:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Maximum Tags Allowed Reached",
          description=f"You've reached the maximum number of tags allowed ({self.max_tags})!" + "\n\n" + "You can remove a tag if desired via `/tags delete`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # If checks pass, go ahead and create the new tag for the user
    await db_create_user_tag(ctx.author.id, tag)
    await ctx.followup.send(
      embed=discord.Embed(
        title="Tag Created Successfully!",
        description=f"You've created a new tag: **{tag}**!" + "\n\n" f"You can tag your badges with this tag now via `/tags tag`",
        color=discord.Color.green()
      ),
      ephemeral=True
    )
    return

  @tags_group.command(
    name="delete",
    description="Delete an existing badge tag"
  )
  @option(
    name="tag",
    description="Name of the tag to delete",
    required=True,
    autocomplete=tags_autocomplete
  )
  async def delete(self, ctx:discord.ApplicationContext, tag:str):
    await ctx.defer(ephemeral=True)

    # Checks
    tag = tag.strip()
    if len(tag) == 0:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You Must Enter A Tag!",
          description=f"Tag name cannot be empty!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if tag == "You don't have any tags yet!":
      await ctx.respond(
        embed=discord.Embed(
          title="No Tags Present",
          description="You'll need to set up some tags first via `/tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    current_user_tags = await db_get_user_badge_tags(ctx.author.id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    if tag not in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Does Not Exist",
          description=f"**{tag}** is not a tag you have created!" + "\n\n" + "You can create a new tag via `/tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # If checks pass, go ahead and delete the tag for the user
    await db_delete_user_tag(ctx.author.id, tag)
    await ctx.followup.send(
      embed=discord.Embed(
        title="Tag Deleted Successfully!",
        description=f"You've deleted the tag: **{tag}**!" + "\n\n" + f"Note that any badges that were previously tagged **{tag}** have been untagged as well.",
        color=discord.Color.green()
      ),
      ephemeral=True
    )
    return


  @tags_group.command(
    name="rename",
    description="Rename an existing badge tag"
  )
  @option(
    name="tag",
    description="Name of the tag to rename",
    required=True,
    autocomplete=tags_autocomplete
  )
  @option(
    name="new_name",
    description="New name for the tag",
    required=True
  )
  async def rename(self, ctx:discord.ApplicationContext, tag:str, new_name:str):
    await ctx.defer(ephemeral=True)

    # Checks
    tag = tag.strip()
    new_name = new_name.strip()
    if len(tag) == 0 or len(new_name) == 0:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You Must Enter A Tag!",
          description=f"Tag name cannot be empty!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if len(new_name) > 24:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Tag Is Too Long!",
          description=f"Tag name cannot exceed 24 characters!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if tag == "You don't have any tags yet!":
      await ctx.respond(
        embed=discord.Embed(
          title="No Tags Present",
          description="You'll need to set up some tags first via `/tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    current_user_tags = await db_get_user_badge_tags(ctx.author.id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    if tag not in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Does Not Exist",
          description=f"**{tag}** is not a tag you have created!" + "\n\n" + "You can create a new tag via `/tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if new_name in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Name Already Exists",
          description=f"You already have a tag named **{new_name}**!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # If checks pass, go ahead and rename the tag for the user
    await db_rename_user_tag(ctx.author.id, tag, new_name)
    await ctx.followup.send(
      embed=discord.Embed(
        title="Tag Renamed Successfully!",
        description=f"You've successfully the tag **{tag}** as **{new_name}**!",
        color=discord.Color.green()
      ),
      ephemeral=True
    )
    return


  @tags_group.command(
    name="tag",
    description="Tag one of your badges!"
  )
  @option(
    name="badge",
    description="Name of the badge to tag",
    required=True,
    autocomplete=user_badges_autocomplete
  )
  async def tag(self, ctx:discord.ApplicationContext, badge:str):
    await ctx.defer(ephemeral=True)

    badge_tags = await db_get_user_badge_tags(ctx.author.id)
    if not badge_tags:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Tags Present",
          description=f"You haven't set up any tags yet!\n\nUse `/tags create` to set up some custom tags first!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    user_badges = await db_get_user_badges(ctx.author.id)
    user_badge_names = [b['badge_name'] for b in user_badges]
    if badge not in user_badge_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Badge Not Present In Inventory",
          description=f"You don't own this badge!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    badge_info = await db_get_badge_info_by_name(badge)
    view = await generateTagBadgeView(ctx.author.id, badge_info)
    embed = discord.Embed(
      title=badge,
      color=discord.Color.dark_purple()
    )
    badge_image = discord.File(fp=f"./images/badges/{badge_info['badge_filename']}", filename=badge_info['badge_filename'])
    embed.set_image(url=f"attachment://{badge_info['badge_filename']}")

    await ctx.followup.send(embed=embed, file=badge_image, view=view, ephemeral=True)


  @tags_group.command(
    name="showcase",
    description="Display a showcase of tagged badges"
  )
  @option(
    name="public",
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="No",
        value="no"
      ),
      discord.OptionChoice(
        name="Yes",
        value="yes"
      )
    ]
  )
  @option(
    name="tag",
    description="Name of the tag to showcase",
    required=True,
    autocomplete=tags_autocomplete
  )
  @commands.check(access_check)
  async def showcase(self, ctx:discord.ApplicationContext, public:str, tag:str):
    public = (public == "yes")

    current_user_tags = await db_get_user_badge_tags(ctx.author.id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    # Checks
    if tag == "You don't have any tags yet!":
      await ctx.respond(
        embed=discord.Embed(
          title="No Tags Present",
          description="You'll need to set up some tags first via `/tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if tag not in current_user_tag_names:
      await ctx.respond(
        embed=discord.Embed(
          title="This Tag Does Not Exist",
          description=f"**{tag}** is not a tag you have created!" + "\n\n" + "You can create a new tag via `/tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    tagged_badges = await db_get_user_tagged_badges(ctx.author.id, tag)
    if not tagged_badges:
      await ctx.respond(
        embed=discord.Embed(
          title="No Badges Tagged",
          description=f"You haven't tagged any badges with {tag} yet!\n\nUse `/tags tag` to tag some badges first!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # If checks pass, go ahead and start the process
    await ctx.defer(ephemeral=not public)

    # Set up text values for paginated pages
    title = f"{remove_emoji(ctx.author.display_name)}'s Tagged Badges - {tag}"
    total_badges_cnt = len(await db_get_all_badge_info())
    tagged_badges_cnt = len(tagged_badges)
    collected = f"{tagged_badges_cnt} TAGGED ON THE USS HOOD"
    filename_prefix = f"badge_list_tagged_{ctx.author.id}-page-"

    badge_images = await generate_paginated_badge_images(ctx.author, 'showcase', tagged_badges, total_badges_cnt, title, collected, filename_prefix)

    embed = discord.Embed(
      title=f"Tagged Badges",
      description=f'{ctx.author.mention} has tagged {tagged_badges_cnt} **{tag}** badges!',
      color=discord.Color.blurple()
    )

    # If we're doing a public display, use the images directly
    # Otherwise private displays can use the paginator
    if not public:
      buttons = [
        pages.PaginatorButton("prev", label="   ⬅   ", style=discord.ButtonStyle.primary, disabled=bool(tagged_badges_cnt <= 30), row=1),
        pages.PaginatorButton(
          "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
        ),
        pages.PaginatorButton("next", label="   ➡   ", style=discord.ButtonStyle.primary, disabled=bool(tagged_badges_cnt <= 30), row=1),
      ]

      pages_list = [
        pages.Page(files=[image], embeds=[embed])
        for image in badge_images
      ]
      paginator = pages.Paginator(
          pages=pages_list,
          show_disabled=True,
          show_indicator=True,
          use_default_buttons=False,
          custom_buttons=buttons,
          loop_pages=True
      )
      await paginator.respond(ctx.interaction, ephemeral=True)
    else:
      # We can only attach up to 10 files per message, so if it's public send them in chunks
      file_chunks = [badge_images[i:i + 10] for i in range(0, len(badge_images), 10)]
      for chunk_index, chunk in enumerate(file_chunks):
        # Only post the embed on the last chunk
        if chunk_index + 1 == len(file_chunks):
          await ctx.followup.send(embed=embed, files=chunk, ephemeral=False)
        else:
          await ctx.followup.send(files=chunk, ephemeral=False)


  @tags_group.command(
    name="carousel",
    description="Cycle through your badges to apply tags"
  )
  @option(
    name="start",
    description="Start from beginning of inventory or resume?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="Resume",
        value="resume"
      ),
      discord.OptionChoice(
        name="Beginning",
        value="beginning"
      )
    ]
  )
  async def carousel(self, ctx:discord.ApplicationContext, start:str):
    await ctx.defer(ephemeral=True)
    user_discord_id = ctx.author.id

    badge_tags = await db_get_user_badge_tags(user_discord_id)
    if not badge_tags:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Tags Present",
          description=f"You haven't set up any tags yet!\n\nUse `/tags create` to set up some custom tags first!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    description = None
    initial_badge_filename = await db_get_last_carousel_tagged_badge_filename(user_discord_id)
    if initial_badge_filename and start == 'resume':
      initial_badge = await db_get_badge_info_by_filename(initial_badge_filename)
      description = "**Resuming:**\n\nThis is the last badge you tagged in your previous Carousel session. You can now re-tag or move and pick up where you left off!"
    else:
      description = "**Starting:** Beginning Carousel from first badge of inventory."
      if start == 'resume':
        description += "\n\nYou had selected 'Resume' but had no previously stored resume location!"
      user_badges = await db_get_user_badges(user_discord_id)
      initial_badge = user_badges[0]

    view = await generateTagCarouselView(user_discord_id, initial_badge)
    embed = discord.Embed(
      title=initial_badge['badge_name'],
      description=description,
      color=discord.Color.dark_purple()
    )
    badge_image = discord.File(fp=f"./images/badges/{initial_badge['badge_filename']}", filename=initial_badge['badge_filename'])
    embed.set_image(url=f"attachment://{initial_badge['badge_filename']}")

    await ctx.followup.send(embed=embed, file=badge_image, view=view, ephemeral=True)

