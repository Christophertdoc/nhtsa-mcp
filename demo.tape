Output demo.gif

Set Shell "zsh"
Set FontSize 18
Set Width 1200
Set Height 600
Set TypingSpeed 50ms
Set Theme "Catppuccin Mocha"
Set Padding 20
Set PlaybackSpeed 1.3

Env PATH "/Users/christopherdougherty/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

# Start the chat session
Type "uv run nhtsa-cli agent chat"
Enter
Sleep 3s

# Question 1
Type "Decode VIN 4S4BL86C764213492 and show me one recall for the vehicle."
Enter
Sleep 10s

# Question 2
Type "Find rim manufacturers that registered parts between 3/1/2023 and 12/31/2023. Show me just the first result."
Enter
Sleep 20s


# Exit the chat
Type "exit"
Enter
Sleep 2s
