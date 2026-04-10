# Pick MA Job

## UX:

1. When running pipeline - create loading animation while it’s 
2. Clear irrelevant jobs - after some set time or with button

## Improvement

1. Pipeline doesn’t work on production
2. Results page:
    1. In filters when applied the words are small. In soft filter user sees score_desc, score_asc, date_desc, date_asc. The names must be the same as before we apply them
    2. Result row text (summary, evaluation, flags, scratchpad) is stretched so that user must scroll right to read it. Make it responsive so that it fits inside user’s current tab size
3. Dashboard
    1. When running pipeline - user sees pending status and when pipeline is finished - user must reload tab to see status completed. It is all must be changed to icons: completed icon and loading icon animation that is independent of tab reload.  As soon as pipeline finished - user must see completed icon. User must not be obliged to reload the tab to see completed icon.
4. Profile
    1. It’s a bit time consuming for user to enter all the information inside input fields. Let’s re-plan this whole tab to be more user friendly. Also nobody will manually put json inside custom rubric because not everyone knows what json is
5. Search Configuration
    1. I can’t add the same platform config twice. User must be able to add as much configs as he wants with different values for the same platform. For example if user wants to add two different configs for upwork but with different search queries - user must be able to do so. Right now they are not able to do so.

## Features

1. We must add main page. Right now it’s only 4 I want to add main page with explantion of what this product does and instructions
2. We must redo overall look of the website. Right now it looks a bit boring with only black and white components. The focus of this is to be eye pleasing and look professional