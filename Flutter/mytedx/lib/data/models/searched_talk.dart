class SearchedTalk {
  final String id;
  final String title;

  SearchedTalk({required this.id, required this.title});

  factory SearchedTalk.fromJSON(Map<String, dynamic> jsonMap) {
    return SearchedTalk(
      id:
          jsonMap['id']?.toString() ??
          DateTime.now().millisecondsSinceEpoch
              .toString(), // Fallback se id è null
      title: jsonMap['title'] ?? 'No Title',
    );
  }
}
