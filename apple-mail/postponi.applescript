-- Postponi - Snooze emails in Apple Mail
-- Configure API_BASE to your server URL
property API_BASE : "https://mail.yourdomain.com"

tell application "Mail"
    set msgs to selection
    if msgs is {} then return
    set msg to item 1 of msgs
    set msgID to message id of msg
    set msgAccount to name of account of mailbox of msg
end tell

set opzioni to {"Domani mattina (8:00)", "Stasera (19:00)", "Weekend (sabato 8:00)", "Settimana prossima (lunedì 8:00)", "Data personalizzata..."}
set scelta to choose from list opzioni with prompt "Quando vuoi ricevere questo messaggio?" default items {"Domani mattina (8:00)"}
if scelta is false then return
set scelta to item 1 of scelta

set oggi to current date
set target to oggi

if scelta is "Domani mattina (8:00)" then
    set target to oggi + (1 * days)
    set time of target to 8 * hours
else if scelta is "Stasera (19:00)" then
    set time of target to 19 * hours
else if scelta is "Weekend (sabato 8:00)" then
    set time of target to 8 * hours
    repeat until weekday of target is Saturday
        set target to target + (1 * days)
    end repeat
else if scelta is "Settimana prossima (lunedì 8:00)" then
    set time of target to 8 * hours
    repeat until weekday of target is Monday
        set target to target + (1 * days)
    end repeat
    if weekday of oggi is Monday then set target to target + (7 * days)
else if scelta is "Data personalizzata..." then
    set dataStr to do shell script "~/.local/bin/datepicker"
    if dataStr is "" then return
    set targetDT to dataStr & "T08:00:00"
    tell application "Mail"
        move msg to mailbox "Postponi" of account of mailbox of msg
    end tell
    do shell script "curl -s -X POST " & API_BASE & "/postpone -H 'Content-Type: application/json' -d '{\"message_url\": \"message://%3C" & msgID & "%3E\", \"target_dt\": \"" & targetDT & "\", \"account\": \"" & msgAccount & "\"}' > /tmp/postponi_curl.log 2>&1 &"
    return
end if

set y to year of target as string
set m to text -2 thru -1 of ("0" & ((month of target as integer) as string))
set d to text -2 thru -1 of ("0" & (day of target as string))
set h to text -2 thru -1 of ("0" & (((time of target) div hours) as string))
set targetDT to y & "-" & m & "-" & d & "T" & h & ":00:00"

tell application "Mail"
    move msg to mailbox "Postponi" of account of mailbox of msg
end tell

do shell script "curl -s -X POST " & API_BASE & "/postpone -H 'Content-Type: application/json' -d '{\"message_url\": \"message://%3C" & msgID & "%3E\", \"target_dt\": \"" & targetDT & "\", \"account\": \"" & msgAccount & "\"}' > /tmp/postponi_curl.log 2>&1 &"
