class ApiConstants {
  static const String getTalksByTagEndpoint =
      'https://q5c249sacb.execute-api.us-east-1.amazonaws.com/default/get-talks-by-tags'; // Assumi un path come /get-talks-by-tag
  static const String getTalkSummaryEndpoint =
      'https://wk1odd3mde.execute-api.us-east-1.amazonaws.com/default/ai-api-agent'; // Assumi un path come /get-talk-summary
  static const String getRelatedTalksEndpoint =
      'https://zk6a6wf4je.execute-api.us-east-1.amazonaws.com/default/get-talks-by-id-neo4j'; // Assumi un path come /get-related-talks
  static const String searchTalksByTitleEndpoint =
      'https://fjpcr39w76.execute-api.us-east-1.amazonaws.com/default/search-by-title'; // Assumi un path come /search-talks
  static const String getAvailableTags =
      'https://0c7phf59uh.execute-api.us-east-1.amazonaws.com/default/get-tags';
  // Parametri API
  static const int talksPerPage = 6;
}
