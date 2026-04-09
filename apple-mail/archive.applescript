-- Archive - Save selected emails to the mail archive
-- Configure API_BASE to your server URL
property API_BASE : "https://mail.yourdomain.com"

tell application "Mail"
    set msgs to selection
    if msgs is {} then return
    repeat with msg in msgs
        set accName to name of account of mailbox of msg
        set msgSource to source of msg
        set tmpFile to "/tmp/mail_archive_" & ((random number from 10000 to 99999) as string) & ".eml"
        set fileRef to open for access POSIX file tmpFile with write permission
        set eof of fileRef to 0
        write msgSource to fileRef
        close access fileRef
        do shell script "curl -s -X POST " & API_BASE & "/archive -F 'account=" & accName & "' -F 'eml=@" & tmpFile & "' > /dev/null 2>&1 && rm " & quoted form of tmpFile & " &"
    end repeat
end tell
