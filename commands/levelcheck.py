from common import *
from handlers.xp import get_user_xp, get_xp_cap_progress, calculate_xp_for_next_level

@bot.slash_command(
  name="levelcheck",
  description="Display how close to your next level you are"
)
async def levelcheck(ctx:discord.ApplicationContext):
  user_xp_data = await get_user_xp(ctx.author.id)
  current_xp = user_xp_data["xp"]
  current_level = user_xp_data["level"]

  previous_level_xp = calculate_xp_for_next_level(current_level - 1)
  base_xp = current_xp - previous_level_xp
  goal_xp = calculate_xp_for_next_level(current_level) - previous_level_xp

  if current_level >= 176:
    # High Levelers - Static Level Up Progression per Every 420 XP
    cap_progress = await get_xp_cap_progress(ctx.author.id)
    if cap_progress is not None:
      base_xp = cap_progress
      goal_xp = 420

  embed = discord.Embed(
    title="Level Up Progress:",
    description=f"**Current Level:** {current_level}\n\n",
    color=discord.Color.random()
  )
  embed.add_field(
    name="Progress",
    value=f"{base_xp}xp / {goal_xp}xp"
  )
  embed.add_field(
    name=f"Total XP",
    value=f"{current_xp}xp"
  )

  await ctx.respond(
    embed=embed,
    ephemeral=True
  )
