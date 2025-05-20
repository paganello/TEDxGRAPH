import 'package:flutter/material.dart';
import 'package:mytedx/data/models/related_talk.dart';

class RelatedTalkTile extends StatelessWidget {
  final RelatedTalk relatedTalk;

  const RelatedTalkTile({super.key, required this.relatedTalk});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      elevation: 1,
      margin: const EdgeInsets.symmetric(vertical: 6.0),
      child: ListTile(
        // leading: Icon(Icons.movie_filter_outlined, color: theme.colorScheme.primary),
        title: Text(relatedTalk.title, style: theme.textTheme.titleMedium),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              relatedTalk.speakers,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.secondary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              relatedTalk.description,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
        // onTap: () {
        //   // Se RelatedTalk avesse un ID, potresti navigare al suo dettaglio:
        //   // if (relatedTalk.id != null) {
        //   //   context.push('${AppRouter.talkDetailRoute}/${relatedTalk.id}');
        //   // }
        // },
      ),
    );
  }
}
