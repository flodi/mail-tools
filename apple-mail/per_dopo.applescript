-- Per Dopo - Move emails to "Later" folder in Apple Mail
tell application "Mail"
    set msgs to selection
    if msgs is {} then return
    repeat with msg in msgs
        set acc to account of mailbox of msg
        move msg to mailbox "Per Dopo" of acc
    end repeat
end tell
