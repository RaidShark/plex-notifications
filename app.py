import time
import datetime
import emailer
import configparser
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer

config = configparser.ConfigParser()
config.read('plex-notifications.ini')

defaults = {
    'base_url':             config['plex']['PLEX_URL'],
    'plex_user':            config['plex']['PLEX_USER'],
    'plex_pass':            config['plex']['PLEX_PASS'],
    'gmail_addr':           config['gmail']['GMAIL_USERNAME'],
    'gmail_pass':           config['gmail']['GMAIL_PASSWORD'],
    'notification_period':  int(config['general']['NOTIFICATION_PERIOD'])
}

plex_local_url = "http://localhost:32400"


def date_to_epoch(timestamp):
    pattern = '%Y-%m-%d %H:%M:%S'
    epoch = int(time.mktime(time.strptime(str(timestamp), pattern)))
    return epoch


html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    '“': "&quot;",
    '”': "&quot;",
    "'": "&apos;",
    "’": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    "-": "&ndash;",
    "–": "&ndash;",
    "½": "&frac12;",
    "⅓": "&frac13;"
}

today = datetime.date.today()
notification_date = today - datetime.timedelta(days=defaults['notification_period'])
notification_epoch = date_to_epoch("%s 00:00:00" % notification_date)

print("Logging into Plex as %s" % defaults['plex_user'])
plexAccount = MyPlexAccount(defaults['plex_user'], defaults['plex_pass'])
plexServer = PlexServer(plex_local_url, plexAccount._token)

recent = plexServer.library.recentlyAdded()
user_emails = [plexAccount.email]
users = plexAccount.users()
for user in users:
    user_emails.append(user.email)

print("Email recipients: %s" % ', '.join(user_emails))

recent_items = []
for video in recent:
    if video.type == "movie" and date_to_epoch(video.addedAt) > notification_epoch:
        recent_item = {}
        recent_item['title'] = "".join(html_escape_table.get(c, c) for c in video.title)
        #  This allows movie posters to be loaded
        recent_item['poster_url'] = video.thumbUrl.replace(plex_local_url, defaults['base_url'])
        recent_item['description'] = "".join(html_escape_table.get(c, c) for c in video.summary)
        recent_items.append(recent_item)

# Make sure that we are only sending out the email when there is something to notify about
print("There are %s new movies this week" % len(recent_items))
if len(recent_items) < 1:
    print("As there are no movies, no email will be sent. Quitting")
    exit()

f = open("plex_email.html", "w+")
f.write('<html>\n  <head>\n    <style>\n%s\n    </style>\n  </head>' % open('email.css', 'r').read())
f.write('  <body>\n    <div class="content">\n      <h1>Now Streaming:</h1>')
for item in recent_items:
    #  Create a card for the movie
    f.write('        <div class="card">\n')
    # Start with the movie poster
    f.write('          <img class="poster" src="%s"  alt="%s movie poster"/>\n' % (item['poster_url'], item['title']))
    #  Add a <div> to hold the text-based data
    f.write('          <div class="info-cell">\n')
    #  Add the Title as a <h2>, and the movie summary
    f.write('            <h2>%s</h2>\n            %s\n' % (item['title'], item['description']))
    #  Wrap it up like a fajita
    f.write('          </div>\n')
    f.write('        </div>\n')
f.write('    </div>\n  </body>\n</html>')
f.close()

print("Sending email")
emailer.send_email(defaults, plexServer.friendlyName, user_emails)
print("Complete")
