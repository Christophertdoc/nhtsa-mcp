Output demo.gif

Set Shell "zsh"
Set FontSize 24
Set Width 1200
Set Height 600
Set TypingSpeed 50ms
Set Theme "Catppuccin Mocha"
Set Padding 20

Env PATH "/Users/christopherdougherty/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

# Start the chat session
Type "uv run nhtsa-cli agent chat"
Enter
Sleep 3s

# Question 1: Decode a VIN
Type "Decode VIN 4S4BL86C764213492 and tell me about that vehicle"
Enter
Sleep 10s

# Question 2: Recalls
Type "Are there any recalls on a 2021 Ford Mustang?"
Enter
Sleep 10s

# Question 3: Crash test ratings
Type "What are the crash test ratings for a 2023 Toyota Camry?"
Enter
Sleep 10s

# Exit the chat
Type "exit"
Enter
Sleep 2s
