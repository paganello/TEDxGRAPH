class TalkSummary {
  final String summary;
  final String talkIdRequested;
  final String originalTitle;

  TalkSummary({
    required this.summary,
    required this.talkIdRequested,
    required this.originalTitle,
  });

  factory TalkSummary.fromJSON(Map<String, dynamic> jsonMap) {
    return TalkSummary(
      summary: jsonMap['summary'] ?? 'Summary not available.',
      talkIdRequested: jsonMap['talk_id_requested']?.toString() ?? '',
      originalTitle: jsonMap['original_title'] ?? '',
    );
  }
}
