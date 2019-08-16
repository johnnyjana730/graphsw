import os
import tensorflow as tf
import numpy as np
from model_TA import KGCN
from train_util_TA import Early_stop_info, Eval_score_info, Train_info_record_sw_emb
from metrics import ndcg_at_k, map_at_k, recall_at_k, hit_ratio_at_k, mrr_at_k
import pickle

# np.random.seed(1)

def train(args, data, trn_info, show_loss, show_topk):
    n_user, n_item, n_entity, n_relation = data[0], data[1], data[2], data[3]
    train_data, eval_data, test_data = data[4], data[5], data[6]
    adj_entity, adj_relation = data[7], data[8]
    user_path, user_path_top_k, item_set_most_pop = data[9], data[10], data[11]

    interaction_table, offset = get_interaction_table(train_data, n_entity) if args.ls_weight > 0 else (None, None)
    early_st_info = Early_stop_info(args,show_topk)
    eval_score_info = Eval_score_info()
    
    # top-K evaluation settings
    user_list, train_record, eval_record, test_record, item_set, k_list = topk_settings(args, show_topk, train_data, eval_data, test_data, n_item, args.save_record_user_list, args.save_model_name)

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as sess:
        model = KGCN(args, n_user, n_entity, n_relation, adj_entity, adj_relation, interaction_table, offset)
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver()

        if args.load_pretrain_emb == True: saver.restore(sess, args.path.misc + str(args.dataset) + '_' + args.save_model_name + '_' + "_model.ckpt")

        print("Model restored.")

        if args.ls_weight > 0:
            interaction_table.init.run()

        for step in range(args.n_epochs):
            # training
            np.random.shuffle(train_data)
            start = 0

            while start + args.batch_size <= train_data.shape[0]:
                _, loss, l2_ls_loss = model.train(sess, get_feed_dict(args, user_path, model, train_data, start, start + args.batch_size))
                start += args.batch_size
                if show_loss:
                    if args.ls_weight > 0: print('start = ', start, 'loss = ', loss, 'ls_loss', l2_ls_loss,end= 'r')
                    else: print('start = ', start, 'loss = ', loss, 'l2_loss', l2_ls_loss,end= 'r')

            # top-K evaluation
            if show_topk:
                precision, recall, ndcg, MAP, hit_ratio = topk_eval(
                    sess, args, user_path_top_k, model, user_list, train_record, eval_record, test_record, item_set_most_pop, k_list, args.batch_size, mode = 'eval')
                n_precision_eval = [round(i, 6) for i in precision]
                n_recall_eval = [round(i, 6) for i in recall]
                n_ndcg_eval = [round(i, 6) for i in ndcg]

                precision, recall, ndcg, MAP, hit_ratio = topk_eval(
                    sess,args, user_path_top_k, model, user_list, train_record, eval_record, test_record, item_set_most_pop, k_list, args.batch_size, mode = 'test')

                n_precision_test = [round(i, 6) for i in precision]
                n_recall_test = [round(i, 6) for i in recall]
                n_ndcg_test = [round(i, 6) for i in ndcg]

                eval_score_info.eval_ndcg_recall_pecision = [n_ndcg_eval, n_recall_eval, n_precision_eval]
                eval_score_info.test_ndcg_recall_pecision = [n_ndcg_test, n_recall_test, n_precision_test]

                trn_info.update_score(step, eval_score_info)
                
                if early_st_info.update_score(step,n_recall_eval[2],sess,model,saver) == True: break
            else:
                # CTR evaluation
                eval_score_info.train_auc_acc_f1 = ctr_eval(args, user_path, sess, model, train_data, args.batch_size)
                eval_score_info.eval_auc_acc_f1 = ctr_eval(args, user_path, sess, model, eval_data, args.batch_size)
                eval_score_info.test_auc_acc_f1 = ctr_eval(args, user_path, sess, model, test_data, args.batch_size)

                trn_info.update_score(step, eval_score_info)
                if early_st_info.update_score(step,eval_score_info.eval_st_score(),sess,model,saver) == True: break

    tf.reset_default_graph()
    
def get_interaction_table(train_data, n_entity):
    offset = len(str(n_entity))
    offset = 10 ** offset
    keys = train_data[:, 0] * offset + train_data[:, 1]
    keys = keys.astype(np.int64)
    values = train_data[:, 2].astype(np.float32)

    interaction_table = tf.contrib.lookup.HashTable(
        tf.contrib.lookup.KeyValueTensorInitializer(keys=keys, values=values), default_value=0.5)
    return interaction_table, offset

def topk_settings(args, show_topk, train_data, eval_data, test_data, n_item, save_record_user_list, save_user_list_name):
    if show_topk:
        user_num = 250
        k_list = [5, 10, 25, 50, 100]
        train_record = get_user_record(train_data, True)
        test_record = get_user_record(test_data, False)
        eval_record = get_user_record(eval_data, False)

        if os.path.exists(args.path.misc + 'user_list_' + save_user_list_name + "_250" + '.pickle') == False:
            user_list = list(set(train_record.keys()) & set(test_record.keys() & (eval_record.keys())))
            user_counter_dict = {user:len(train_record[user]) for user in user_list}
            user_counter_dict = sorted(user_counter_dict.items(), key=lambda x: x[1], reverse=True)
            user_counter_dict = user_counter_dict[:user_num]
            user_list = [user_set[0] for user_set in user_counter_dict]

            if len(user_list) > user_num:
                user_list = np.random.choice(user_list, size=user_num, replace=False)
            with open(args.path.misc + 'user_list_' + save_user_list_name + "_250" + '.pickle', 'wb') as fp:
                pickle.dump(user_list, fp)
        print('user_list_load')
        with open (args.path.misc + 'user_list_' + save_user_list_name + "_250" + '.pickle', 'rb') as fp:
            user_list = pickle.load(fp)
        item_set = set(list(range(n_item)))
        return user_list, train_record, eval_record, test_record, item_set, k_list
    else:
        return [None] * 6


def get_feed_dict(args, user_path, model, data, start, end):
    
    feed_dict = {model.user_indices: data[start:end, 0],
                 model.item_indices: data[start:end, 1],
                 model.labels: data[start:end, 2]}
    if args.ls_turn_up == True:
        feed_dict[model.ls_turn_up] = 1.0
    else:
        feed_dict[model.ls_turn_up] = 0
        
    feed_dict[model.lr_placeholder] = args.lr
    return feed_dict


def ctr_eval(args, user_path, sess, model, data, batch_size):
    start = 0
    auc_list = []
    acc_list = []
    f1_list = []
    while start + batch_size <= data.shape[0]:
        auc, acc,  f1 = model.eval(sess, get_feed_dict(args, user_path, model, data, start, start + args.batch_size))
        auc_list.append(auc)
        acc_list.append(acc)
        f1_list.append(f1)
        start += batch_size
    return float(np.mean(auc_list)), float(np.mean(acc_list)), float(np.mean(f1_list))


def topk_eval(sess, args, user_path_top_k, model, user_list, train_record, eval_record, test_record, item_set, k_list, batch_size, mode = 'test'):
    precision_list = {k: [] for k in k_list}
    recall_list = {k: [] for k in k_list}
    MAP_list = {k: [] for k in k_list}
    hit_ratio_list = {k: [] for k in k_list}
    ndcg_list = {k: [] for k in k_list}

    for user in user_list:
        if mode == 'eval': ref_user = eval_record
        else: ref_user = test_record
        if user in ref_user:

            test_item_list = list(item_set - train_record[user])
            # test_item_list = test_item_list[:1000]
            item_score_map = dict()
            start = 0
            while start + batch_size <= len(test_item_list):
                items, scores = model.get_scores(sess, {model.user_indices: [user] * batch_size,
                                                    model.item_indices: test_item_list[start:start + batch_size]})

                for item, score in zip(items, scores):
                    item_score_map[item] = score
                start += batch_size

            # padding the last incomplete minibatch if exists
            if start < len(test_item_list):
                items, scores = model.get_scores(
                    sess, {model.user_indices: [user] * batch_size,
                           model.item_indices: test_item_list[start:] + [test_item_list[-1]] * (
                                   batch_size - len(test_item_list) + start)})            

                for item, score in zip(items, scores):
                    item_score_map[item] = score

            item_score_pair_sorted = sorted(item_score_map.items(), key=lambda x: x[1], reverse=True)
            item_sorted = [i[0] for i in item_score_pair_sorted]

            for k in k_list:
                recall_list[k].append(recall_at_k(item_sorted,ref_user[user],k))

            # ndcg
            r_hit = []
            for i in item_sorted[:k]:
                if i in ref_user[user]:
                    r_hit.append(1)
                else:
                    r_hit.append(0)
            for k in k_list:
                ndcg_list[k].append(ndcg_at_k(r_hit,k))

    precision = [np.mean(precision_list[k]) for k in k_list]
    recall = [np.mean(recall_list[k]) for k in k_list]
    ndcg = [np.mean(ndcg_list[k]) for k in k_list]
    # MAP = [np.mean(MAP_list[k]) for k in k_list]
    # hit_ratio = [np.mean(hit_ratio_list[k]) for k in k_list]

    return precision, recall, ndcg, None, None


def get_user_record(data, is_train):
    user_history_dict = dict()
    for interaction in data:
        user = interaction[0]
        item = interaction[1]
        label = interaction[2]
        if label == 1:
            if user not in user_history_dict:
                user_history_dict[user] = set()
            user_history_dict[user].add(item)
    return user_history_dict
