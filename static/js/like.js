function like(file_uuid) {
  const likeCount = document.getElementById(`likes-count-${file_uuid}`);
  const likeButton = document.getElementById(`like-button-${file_uuid}`);

  fetch(`/like-post/${file_uuid}`, { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      likeCount.innerHTML = data["likes"];
      if (data["liked"] === true) {
        likeButton.className = "fas fa-thumbs-up";
      } else {
        likeButton.className = "far fa-thumbs-up";
      }
    })
    .catch((e) => alert("Could not like post."));
}
