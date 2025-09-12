# 🔧 Reaction Events Troubleshooting Guide

## ✅ **SOLUTION: Using Raw Reaction Events**

Your bot now uses **`on_raw_reaction_add`** and **`on_raw_reaction_remove`** instead of the regular reaction events. This completely solves the caching problem!

### 🎯 **Why Raw Events Are Better:**

✅ **No Cache Dependency** - Works for ALL messages, even after bot restart
✅ **Always Reliable** - Never misses reaction events
✅ **Better Performance** - Doesn't require message caching
✅ **Future-Proof** - Handles messages from before bot startup

### 📋 **Required Bot Intents (Discord Developer Portal):**
- ✅ `Message Content Intent`
- ✅ `Server Members Intent`
- ✅ `Presence Intent` (recommended)

### 💻 **Code Configuration:**
```python
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.reactions = True  # Required for raw reaction events
intents.members = True
```

### 2. **Bot Permissions in Discord Server**

Ensure your bot has these permissions in the server/channel:
- ✅ `Read Messages`
- ✅ `Send Messages`
- ✅ `Read Message History`
- ✅ `Add Reactions`
- ✅ `Manage Messages` (for removing invalid reactions)
- ✅ `Use Slash Commands`

### 3. **Testing the Fix**

#### 📝 **Debug Commands**
Use the new debug command to troubleshoot:

```bash
# List all movies in the current channel
!debug_ratings

# Get detailed info for a specific movie message
!debug_ratings 1234567890123456789
```

#### 🐛 **Console Debugging**
The bot now includes comprehensive debug logging. Watch your console for:
```
DEBUG: Reaction added by username (ID: 123456) to message 987654321098765432 in channel 111111111111111111
DEBUG: Found movie data for IMDB ID: tt0111161
DEBUG: Validating emoji: '8️⃣'
DEBUG: User 123456 has rated movie tt0111161: False
DEBUG: Converted emoji '8️⃣' to rating value: 8
DEBUG: Saving rating 8 for user 123456
DEBUG: Rating save result: True
DEBUG: Rating saved successfully, updating embed
DEBUG: Embed updated successfully
```

### 4. **Common Error Scenarios**

#### **❌ "Bot doesn't have permission to manage reactions"**
- **Cause**: Missing `Manage Messages` permission
- **Fix**: Add the permission to the bot's role in Discord server settings

#### **❌ No debug output when reacting**
- **Cause**: Reaction events not firing
- **Fix**: Check Discord Developer Portal intents and restart bot

#### **❌ "Message has no embeds, fetching from API..."**
- **Cause**: Message not cached
- **Fix**: This is normal behavior - the bot will fetch the message automatically

#### **❌ "Message X is not a movie message"**
- **Cause**: User reacted to a non-movie message
- **Fix**: Only react to movie embed messages (this is expected behavior)

### 5. **Database Migration**

Make sure to apply the database migration:
```bash
npx supabase db push
```

The migration creates the `ratings` table required for the new system.

### 6. **Step-by-Step Testing**

1. **Start the bot** and check console for "Logged in as..." message
2. **Post an IMDB URL** in the configured channel
3. **Wait for the embed** to appear
4. **React with a digit emoji** (0️⃣-9️⃣)
5. **Check console debug output**
6. **Use `!debug_ratings`** to verify ratings are being saved
7. **Verify embed updates** with the new average rating

### 7. **Additional Fixes Applied**

#### **✅ Enhanced Error Handling**
- Added comprehensive try-catch blocks
- Graceful handling of permission errors
- Automatic message fetching for uncached messages
- Detailed error logging

#### **✅ Message Caching**
- Bot now fetches message content if not cached
- Handles cases where message embeds aren't immediately available

#### **✅ Guild Context Handling**
- Proper handling of guild vs DM contexts
- Null-safe guild ID extraction

### 8. **Still Having Issues?**

If the reaction events still aren't working:

1. **Check Discord Developer Portal** - Ensure all intents are enabled
2. **Restart the bot** after changing intents
3. **Verify bot permissions** in your Discord server
4. **Check bot logs** for any error messages
5. **Test with the debug command** to isolate the issue

### 9. **Performance Considerations**

The enhanced system includes:
- **In-memory caching** (5-minute TTL) for rating statistics
- **Database indexing** for fast queries
- **Batch operations** for efficient updates
- **Rate limiting** ready (can be added if needed)

### 10. **Next Steps**

Once reaction events are working:
1. Remove debug print statements for production
2. Consider adding Redis for distributed caching
3. Monitor performance and add metrics if needed
4. Add user feedback features (rating history, etc.)

The system is now much more robust and should handle reaction events reliably with proper configuration.