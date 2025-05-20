import 'package:flutter/material.dart';
import 'package:mytedx/data/models/talk.dart';
import 'package:mytedx/navigation/app_router.dart';
import 'package:go_router/go_router.dart';

class TalkCard extends StatelessWidget {
  final Talk talk;

  const TalkCard({super.key, required this.talk});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 16.0),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: () {
          // Usare talk.id o talk.slug a seconda di cosa si aspetta la route per l'identificativo
          context.push('${AppRouter.talkDetailRoute}/${talk.id}', extra: talk);
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                talk.title,
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 8),
              Text(
                talk.mainSpeaker,
                style: theme.textTheme.titleMedium?.copyWith(
                  color: theme.colorScheme.secondary,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                talk.details,
                style: theme.textTheme.bodyMedium,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
              if (talk.keyPhrases.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 6.0,
                  runSpacing: 4.0,
                  children:
                      talk.keyPhrases
                          .take(5)
                          .map(
                            (phrase) => Chip(
                              // Mostra solo le prime 5 keyphrases
                              label: Text(
                                phrase,
                                style: theme.textTheme.bodySmall?.copyWith(
                                  fontSize: 10,
                                ),
                              ),
                              backgroundColor: theme.colorScheme.primary
                                  .withOpacity(0.1),
                              labelPadding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 0,
                              ),
                              materialTapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                            ),
                          )
                          .toList(),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
