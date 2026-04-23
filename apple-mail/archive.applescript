-- Archive - Save selected emails to the mail archive
-- Requires: ~/.local/bin/mail_archive.py (installed by setup.sh)
-- Mail is released immediately after collecting message IDs

set msgDataList to {}
tell application "Mail"
    set msgs to selection
    if msgs is {} then return
    repeat with msg in msgs
        set msgNum to id of msg
        set accName to name of account of mailbox of msg
        set end of msgDataList to {theNum: msgNum, theAccount: accName}
    end repeat
end tell

-- Mail is free from here
repeat with msgData in msgDataList
    set msgNum to theNum of msgData as string
    set accName to theAccount of msgData
    do shell script "nohup python3 ~/.local/bin/mail_archive.py " & quoted form of msgNum & " " & quoted form of accName & " > /dev/null 2>&1 &"
end repeat
