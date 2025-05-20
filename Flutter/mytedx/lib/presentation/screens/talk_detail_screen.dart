import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mytedx/data/models/talk.dart';
import 'package:mytedx/presentation/providers/talk_providers.dart';
import 'package:mytedx/presentation/widgets/common_widgets.dart';
import 'package:mytedx/presentation/widgets/related_talk_tile.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

class TalkDetailScreen extends ConsumerWidget {
  final Talk talk;

  const TalkDetailScreen({super.key, required this.talk});

  Future<void> _launchURL(BuildContext context, String urlString) async {
    final Uri? url = Uri.tryParse(urlString);
    if (url != null && await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } else {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Could not launch $urlString')));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final summaryAsync = ref.watch(talkSummaryProvider(talk.id)); // Usa talk.id
    final relatedTalksAsync = ref.watch(
      relatedTalksProvider(talk.id),
    ); // Usa talk.id

    return Scaffold(
      appBar: AppBar(title: Text(talk.title, overflow: TextOverflow.ellipsis)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            // Titolo e Speaker
            Text(
              talk.title,
              style: theme.textTheme.displaySmall?.copyWith(
                color: theme.colorScheme.primary,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(
                  FontAwesomeIcons.microphoneLines,
                  size: 16,
                  color: theme.colorScheme.secondary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    talk.mainSpeaker,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
            if (talk.publishedAt != null || talk.duration != null) ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  if (talk.publishedAt != null) ...[
                    Icon(
                      Icons.calendar_today,
                      size: 14,
                      color: theme.colorScheme.secondary.withOpacity(0.7),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      _formatPublishedAt(talk.publishedAt!),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.secondary.withOpacity(0.9),
                      ),
                    ),
                    const SizedBox(width: 12),
                  ],
                  if (talk.duration != null) ...[
                    Icon(
                      Icons.timer_outlined,
                      size: 14,
                      color: theme.colorScheme.secondary.withOpacity(0.7),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      _formatDuration(talk.duration!),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.secondary.withOpacity(0.9),
                      ),
                    ),
                  ],
                ],
              ),
            ],

            const SizedBox(height: 16),
            Divider(color: theme.colorScheme.secondary.withOpacity(0.2)),
            const SizedBox(height: 16),

            // Descrizione
            _buildSectionTitle(
              context,
              'About this Talk',
              FontAwesomeIcons.circleInfo,
            ),
            Text(talk.details, style: theme.textTheme.bodyLarge),
            const SizedBox(height: 24),

            // Riassunto (da HuggingFace)
            _buildSectionTitle(context, 'AI Summary', FontAwesomeIcons.brain),
            summaryAsync.when(
              data:
                  (summaryData) => Text(
                    summaryData.summary,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontStyle: FontStyle.italic,
                    ),
                  ),
              loading: () => const Center(child: AppLoader(size: 25)),
              error:
                  (err, stack) => Text(
                    'Could not load summary: ${err.toString()}',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.error,
                    ),
                  ),
            ),
            const SizedBox(height: 24),

            // Key Phrases
            if (talk.keyPhrases.isNotEmpty) ...[
              _buildSectionTitle(context, 'Key Phrases', FontAwesomeIcons.tags),
              Wrap(
                spacing: 8.0,
                runSpacing: 4.0,
                children:
                    talk.keyPhrases
                        .map(
                          (phrase) => Chip(
                            label: Text(
                              phrase,
                              style: theme.textTheme.bodySmall,
                            ),
                            backgroundColor: theme.colorScheme.primary
                                .withOpacity(0.1),
                          ),
                        )
                        .toList(),
              ),
              const SizedBox(height: 24),
            ],

            // Talk Correlati (da Neo4j)
            _buildSectionTitle(
              context,
              'Related Talks',
              FontAwesomeIcons.peopleGroup,
            ),
            relatedTalksAsync.when(
              data: (relatedTalksList) {
                if (relatedTalksList.isEmpty) {
                  return const Text(
                    'No related talks found.',
                    style: TextStyle(fontStyle: FontStyle.italic),
                  );
                }
                return Column(
                  children:
                      relatedTalksList
                          .map((rt) => RelatedTalkTile(relatedTalk: rt))
                          .toList(),
                );
              },
              loading: () => const Center(child: AppLoader(size: 25)),
              error:
                  (err, stack) => Text(
                    'Could not load related talks: ${err.toString()}',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.error,
                    ),
                  ),
            ),
            const SizedBox(height: 32),

            // Pulsante URL
            if (talk.url.isNotEmpty)
              Center(
                child: ElevatedButton.icon(
                  icon: const Icon(
                    FontAwesomeIcons.upRightFromSquare,
                    size: 16,
                  ),
                  label: const Text('Watch on TED.com'),
                  onPressed: () => _launchURL(context, talk.url),
                ),
              ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(BuildContext context, String title, IconData icon) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Row(
        children: [
          FaIcon(icon, size: 18, color: theme.colorScheme.primary),
          const SizedBox(width: 8),
          Text(
            title,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  String _formatPublishedAt(String publishedAtIso) {
    try {
      final dt = DateTime.parse(publishedAtIso);
      return "${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}";
    } catch (e) {
      return publishedAtIso; // Ritorna la stringa originale se il parsing fallisce
    }
  }

  String _formatDuration(int totalSeconds) {
    final duration = Duration(seconds: totalSeconds);
    String twoDigits(int n) => n.toString().padLeft(2, "0");
    final hours = twoDigits(duration.inHours);
    final minutes = twoDigits(duration.inMinutes.remainder(60));
    final seconds = twoDigits(duration.inSeconds.remainder(60));
    if (duration.inHours > 0) {
      return "$hours:$minutes:$seconds";
    } else {
      return "$minutes:$seconds";
    }
  }
}
