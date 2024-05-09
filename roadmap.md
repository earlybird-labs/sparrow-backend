- Keep a running context of what the thread is talking about.
  - We use the channel wide context + every new thread message to keep a running "context"
  - For example:
    - if on the 7th message a user says "What do u think is causing X"
    - Its important to know what X is
  - Possible good application for entity graph with NetworkX
    - example convo:
      - msg 1: "The new feature we implemented seems to be causing the website to not load correctly on mobile devices."
      - msg 2: "I don't think it's the new feature because we changed the import to not affect the mobile layout."
      - msg 3: "Could it be related to the recent CSS changes we made to improve the responsiveness of the site?"
      - msg 4: "I just checked the console logs, and there are some error messages pointing to a conflict between the new JavaScript library and the existing code."
      - msg 5: "Okay, let's try to isolate the problem. Can you share the specific error messages you're seeing?"
    - example entity graph:
      ```
        [
          ('new feature', 'website', 'seems to be causing not load correctly on mobile devices'),
          ('import', 'mobile layout', 'changed to not affect'),
          ('CSS changes', 'responsiveness of the site', 'were made to improve'),
          ('console logs', 'error messages', 'are showing'),
          ('error messages', 'conflict', 'are pointing to'),
          ('conflict', 'new JavaScript library', 'is between'),
          ('conflict', 'existing code', 'is between')
        ]
      ```
- 
