jq -r '.log.entries[].response.content.text' \
| perl -nle 'next unless /transactionPagingList/; print "$_,"' \
| perl -0777 -ne 's/,\s*$//; print "[\n$_\n]"' \
| jq '[.[] | .data.transactionPagingList.itemList[]]'
