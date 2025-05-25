class SearchedTalk {
  final String id;
  final String title;
  final String details;
  final String mainSpeaker;

  SearchedTalk({required this.id, required this.title, required this.details, required this.mainSpeaker});

  factory SearchedTalk.fromJSON(Map<String, dynamic> jsonMap) {
    return SearchedTalk(
      id:
          jsonMap['id']?.toString() ??
          DateTime.now().millisecondsSinceEpoch
              .toString(), // Fallback se id è null
      title: jsonMap['title'] ?? 'No Title',
      details: jsonMap['description'] ?? 'No Description',
      mainSpeaker: (jsonMap['speakers'] ??
              jsonMap['mainSpeaker'] ??
              "Unknown Speaker"), // Aggiunto fallback per 'mainSpeaker'
    );
  }
}
