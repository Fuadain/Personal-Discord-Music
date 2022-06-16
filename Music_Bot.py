
import discord
from discord.ext import commands,tasks
import os
import youtube_dl
import asyncio


DISCORD_TOKEN = "Insert Token here"

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='?',intents=intents)

# possibly add list (or dictionary)
# of server ids, each with own song queues,
# adding queue when bot joins voice channel, and removing when leaving
song_queue = []


youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    #'noplaylist': True,    prevents playlist link from individual video entry if true
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

async def getDirectUrl(url, loop=None, enqueuing=False):
    loop = loop or asyncio.get_event_loop()
    urlData = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

    if 'entries' in urlData:
        newPlaylist = []
        for i, item in enumerate(urlData['entries']):
            newPlaylist.append(
                    {
                        'title':urlData['entries'][i]['title'], 
                        'url':urlData['entries'][i]['url']
                    })
            #print(urlData['entries'][i]['title'])
        if(enqueuing==True):
            print("queuing list")
            return newPlaylist
        else:
            song_queue.extend(newPlaylist)
            return song_queue.pop(0)
    else:
        return {'title':urlData['title'], 'url':urlData['url']}

#https://stackoverflow.com/questions/53605422/discord-py-music-bot-how-to-combine-a-play-and-queue-command
@bot.command(name='play', help='To play song')
async def play(ctx,url):
    try :
        server = ctx.message.guild
        voice_channel = server.voice_client
        #join vc, ADD join only on not in vc
        await join(ctx, play_join=True)             
        if not(voice_channel.is_playing()):
            async with ctx.typing():
                songData = await getDirectUrl(url, loop=bot.loop)
                songUrl = songData['url']
                voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=songUrl), 
                                   after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
                
            await ctx.send('Now playing: {}'.format(songData['title']))
        else:
            print('Adding to queue')
            #if queuing playlist, song queue and playlist merge, otherwise append what would be singular song
            async with ctx.typing():
                songData = await getDirectUrl(url, loop=bot.loop, enqueuing=True)
                if type(songData) == list:
                    song_queue.extend(songData)
                else:
                    song_queue.append(songData)
            await ctx.send("Added to queue")
    except:
        await ctx.send("The bot is not connected to a voice channel. (or an error occurred)")


#https://stackoverflow.com/questions/61276362/how-to-play-the-next-song-after-first-finished-discord-bot?rq=1
async def play_next(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    
    if len(song_queue) > 0:
        songData = song_queue.pop(0)
        songUrl = songData['url']
        try:
            voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=songUrl),
                               after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            await ctx.send("Playing next song: {}".format(songData['title']))
        except:
            await ctx.send("An error occurred")
    else:
        await asyncio.sleep(300) #wait 5 minutes
        if not voice_channel.is_playing():
            voice_channel.disconnect(ctx)
            ctx.send("AFK, disconnecting now")
    #alternative could work
    #if len(song_queue) > 0:
    #    url = song_queue.pop(0)
    #    await play(ctx, url)
        

@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx, play_join = False):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if play_join and voice_client:
       return
    elif voice_client:
       await ctx.send('Already connected to voice channel')
       return
    
    await channel.connect()


@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")
 
        
@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play command")
    

@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
        song_queue.clear()
    else:
        await ctx.send("The bot is not connected to a voice channel.")
    

@bot.command(name='skip', help='Skips the song')
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='queue', help='Lists the queue')
async def queue(ctx):
    queueListString = ""
    for i, song in enumerate(song_queue):
        queueListString += "{num}) {title}\n".format(num=str(i+1), title=song['title'])
    await ctx.send("Queue: \n{}".format(queueListString))


@bot.event
async def on_ready():
    print('Running!')
    #for guild in bot.guilds:
        #for channel in guild.text_channels :
            #if str(channel) == "bot-channel" :
                #await channel.send('Unleashed..')


@bot.command()
async def tell_me_about_yourself(ctx):
    text = "I have been unleashed (?help for more)\n :)"
    await ctx.send(text)


if __name__ == "__main__" :
    bot.run(DISCORD_TOKEN)