tell application "Mail"
    repeat with acc in accounts
        repeat with folder_name in {"Junk", "Posta indesiderata", "Trash", "Cestino", "Deleted Messages", "Deleted Items", "Archive", "Archivio", "[Gmail]/All Mail"}
            try
                set mb to mailbox folder_name of acc
                set unread_msgs to (messages of mb whose read status is false)
                repeat with msg in unread_msgs
                    set read status of msg to true
                end repeat
            end try
        end repeat
    end repeat
end tell
