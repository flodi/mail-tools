tell application "Mail"
    set msgs to selection
    if msgs is {} then return
    set msg to item 1 of msgs
    set acc to account of mailbox of msg
    set accName to name of acc
    set msgID to message id of msg
end tell

if accName is "Bluecube" then
    do shell script "/usr/bin/curl -s -X POST https://mail.srvc.es/gmail/move -H 'Content-Type: application/json' -d '{\"email\": \"f.lodi@bluecube.it\", \"message_id\": \"" & msgID & "\", \"target_folder\": \"Per Dopo\"}'"
    -- Forza refresh aprendo e chiudendo le mailbox
    tell application "Mail"
        set mb to mailbox "INBOX" of account "Bluecube"
        check for new mail for account "Bluecube"
    end tell
else
    tell application "Mail"
        move msg to mailbox "Per Dopo" of acc
    end tell
end if
