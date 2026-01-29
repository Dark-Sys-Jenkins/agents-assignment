docker run --rm `
  --env-file .env `
  -p 7880:7880 `
  -p 7881:7881 `
  -v ${PWD}/agent-config.yaml:/etc/livekit.yaml `
  livekit/livekit-server `
  --config /etc/livekit.yaml `
  --keys "localdev1: someverylongsecretstringthatissafely32chars"
