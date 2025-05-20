class RelatedTalk {
  final String title;
  final String speakers;
  final String description;
  // Se l'API Get_Connected_Nodes_From_Neo4j restituisce anche un ID per navigare al dettaglio
  // del talk correlato, aggiungilo qui. Il codice fornito non lo include esplicitamente.
  // final String? id; // Esempio

  RelatedTalk({
    required this.title,
    required this.speakers,
    required this.description,
    // this.id,
  });

  factory RelatedTalk.fromJSON(Map<String, dynamic> jsonMap) {
    return RelatedTalk(
      title: jsonMap['title'] ?? 'No Title',
      speakers: jsonMap['speakers'] ?? 'Unknown Speaker',
      description: jsonMap['description'] ?? 'No Description',
      // id: jsonMap['id']?.toString(),
    );
  }
}
