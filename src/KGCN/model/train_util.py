import os
import time

class Early_stop_info:
    def __init__(self,args,show_topk):
        self.best_eval_f1_ndcg = -float('inf')
        self.best_eval_f1_ndcg_save_para = -float('inf')
        self.training_start_time = time.time()
        self.earlystop_counter = 0
        self.args = args
        self.show_topk = show_topk
        self.early_decrease_lr = args.early_decrease_lr
        self.early_stop = args.early_stop
        self.tolerance = args.tolerance
        self.save_final_model = args.save_final_model
    def update_score(self,epoch,eval_score,sess,model,saver):
        f1_or_ndcg = eval_score
        if f1_or_ndcg > self.best_eval_f1_ndcg_save_para:
            self.best_eval_f1_ndcg_save_para = f1_or_ndcg
            if self.save_final_model == True:
                model.save_pretrain_emb_fuc(sess)
                print("Model all parameter saved.")
        if epoch + 1 > self.tolerance:
            if f1_or_ndcg > self.best_eval_f1_ndcg:
                self.best_eval_f1_ndcg = f1_or_ndcg
                self.earlystop_counter = 0
            else: self.earlystop_counter += 1
            if self.earlystop_counter >= self.early_stop:
                training_time = time.time() - self.training_start_time
                print("EarlyStopping!")
                print(f"Total training time {training_time:.2f}")
                return True

class Eval_score_info:
    def __init__(self):
        self.train_auc_acc_f1 = [0 for _ in range(3)]
        self.eval_auc_acc_f1 = [0 for _ in range(3)]
        self.test_auc_acc_f1 = [0 for _ in range(3)]

        self.train_ndcg_recall_pecision = [[0 for i in range(5)] for _ in range(3)]
        self.eval_ndcg_recall_pecision = [[0 for i in range(5)] for _ in range(3)]
        self.test_ndcg_recall_pecision = [[0 for i in range(5)] for _ in range(3)]

        self.eval_precision = 0
        self.eval_recall = 0
        self.eval_ndcg = 0
        self.test_precision = 0
        self.test_recall = 0
        self.test_ndcg = 0
    def eval_st_score(self):
        return self.eval_auc_acc_f1[0]


class Train_info_record_sw_emb:
    def __init__(self,args):
        # cur_tim = time.strftime("%Y%m%d-%H%M%S")
        cur_tim = time.strftime("%Y%m%d")
        self.folder_path = f"{args.path.output}{str(cur_tim)}__{args.log_name}.log"
        self.folder_path_best = f"{args.path.output}{str(cur_tim)}_best_score_{args.log_name}.log"

        self.emb_score_auc = [[0 for _ in range(5)]  for _ in range(4)]
        self.emb_score_acc = [[0 for _ in range(5)]  for _ in range(4)]
        self.emb_score_f1 = [[0 for _ in range(5)]  for _ in range(4)]
        self.emb_score_recall = [[0 for _ in range(5)]  for _ in range(4)]

        self.emb_score_auc_tmp = [[[0,0] for _ in range(5)]  for _ in range(4)]
        self.emb_score_acc_tmp = [[[0,0] for _ in range(5)]  for _ in range(4)]
        self.emb_score_f1_tmp = [[[0,0] for _ in range(5)]  for _ in range(4)]
        self.emb_score_recall_tmp = [[[0,0] for _ in range(5)]  for _ in range(4)]

        self.sw_early_stop = 0
        self.counter = 1

    def update_cur_train_info(self,args):    

        self.hop = args.n_iter

        self.ls_turn_up = args.ls_turn_up
        self.load_pretrain_emb = args.load_pretrain_emb

        self.max_train_auc = 0
        self.max_train_acc = 0
        self.max_train_f1 = 0
        self.max_eval_auc = 0
        self.max_eval_acc = 0
        self.max_eval_f1 = 0
        self.max_test_auc = 0
        self.max_test_acc = 0
        self.max_test_f1 = 0
        self.update_call = False

        self.max_eval_recall = 0
        self.max_test_recall = 0

        self.max_eval_ndcg = 0
        self.max_test_ndcg = 0

        train_log = open(self.folder_path, 'a')
        train_log.write(f"lr = {args.lr}, hop = {args.n_iter}, np.epoch = {args.epoch}, neighbor_sample_size = {str(args.neighbor_sample_size)}\n")
        train_log.write(f"dataset = {args.dataset}, dim = {args.dim}, batch_size = {args.batch_size}, use_nb_rate = {args.use_neighbor_rate}, l2_weight = {args.l2_weight}, ls_weight = {args.ls_weight}, ls_true_up = {args.ls_turn_up} \n")
        cur_tim = time.strftime("%Y%m%d-%H%M%S")  
        train_log.write(f"pretrain_emb = {args.load_pretrain_emb}, tolerance = {args.tolerance}, early_decrease_lr = {args.early_decrease_lr}\n")
        train_log.close()
        train_log = open(self.folder_path_best, 'a')
        train_log.write(f"lr = {args.lr}, hop = {args.n_iter}, np.epoch = {args.epoch}, neighbor_sample_size = {str(args.neighbor_sample_size)}\n")
        train_log.write(f"dataset = {args.dataset}, dim = {args.dim}, batch_size = {args.batch_size}, use_nb_rate = {args.use_neighbor_rate}, l2_weight = {args.l2_weight}, ls_weight = {args.ls_weight}, ls_true_up = {args.ls_turn_up} \n")
        cur_tim = time.strftime("%Y%m%d-%H%M%S")
        train_log.write(f"pretrain_emb = {args.load_pretrain_emb}, tolerance = {args.tolerance}, early_decrease_lr = {args.early_decrease_lr}\n")
        train_log.close()


    def update_score(self, step, eval_score_info):
        train_auc, train_acc, train_f1 = eval_score_info.train_auc_acc_f1[0], eval_score_info.train_auc_acc_f1[1], eval_score_info.train_auc_acc_f1[2]
        eval_auc, eval_acc, eval_f1 = eval_score_info.eval_auc_acc_f1[0], eval_score_info.eval_auc_acc_f1[1], eval_score_info.eval_auc_acc_f1[2]
        test_auc, test_acc, test_f1 =  eval_score_info.test_auc_acc_f1[0], eval_score_info.test_auc_acc_f1[1], eval_score_info.test_auc_acc_f1[2]

        print('epoch %d  train auc: %.4f acc: %.4f f1: %.4f eval auc: %.4f acc: %.4f f1: %.4f test auc: %.4f acc: %.4f f1: %.4f'
                  % (step, train_auc, train_acc, train_f1, eval_auc, eval_acc, eval_f1, test_auc, test_acc, test_f1), end = '\r')
        train_log = open(self.folder_path, 'a')
        train_log.write('epoch %d  train auc: %.4f acc: %.4f f1: %.4f  eval auc: %.4f acc: %.4f f1: %.4f  test auc: %.4f acc: %.4f f1: %.4f \n'
                  % (step, train_auc, train_acc, train_f1, eval_auc, eval_acc, eval_f1, test_auc, test_acc, test_f1))
        train_log.close()

        if train_auc > self.max_train_auc:
            self.max_train_auc =  train_auc
            self.max_train_acc = train_acc
            self.max_train_f1 = train_f1

        if eval_auc > self.max_eval_auc:
            self.max_eval_auc =  eval_auc
            self.max_eval_acc = eval_acc
            self.max_eval_f1 = eval_f1
            self.max_test_auc = test_auc
            self.max_test_acc = test_acc
            self.max_test_f1 =  test_f1
            self.update_call = True
        else:
            self.update_call = False

    def check_update_recall(self):
        return self.update_call

    def update_recall(self, step, n_precision_eval, n_recall_eval, n_ndcg_eval, n_precision_test, n_recall_test, n_ndcg_test):

        train_log = open(self.folder_path, 'a')
        train_log.write(f"step = {step}, eval ndcg = {n_ndcg_eval} ")
        train_log.write(f"step = {step}, test ndcg = {n_ndcg_test} \n")
        train_log.write(f"step = {step}, eval recall = {n_recall_eval} ")
        train_log.write(f"step = {step}, test recall = {n_recall_test} \n")
        train_log.close()

        if n_ndcg_eval[2] >  self.max_eval_ndcg:
            self.max_eval_ndcg = n_ndcg_eval[2]
            self.max_eval_recall = n_recall_eval[2]
            self.max_test_recall = n_recall_test[2]
            self.update_call = False

    def train_over(self,tags = 0):
        
        train_log = open(self.folder_path, 'a')
        train_log.write("*"*100)
        train_log.write("\n")

        print('best_score  max_train auc: %.4f acc: %.4f max_f1: %.4f  max_eval auc: %.4f acc: %.4f max_f1: %.4f max_test auc: %.4f acc: %.4f max_f1: %.4f'
                  % (self.max_train_auc, self.max_train_acc, self.max_train_f1, self.max_eval_auc, self.max_eval_acc, self.max_eval_f1, self.max_test_auc, self.max_test_acc, self.max_test_f1))
        train_log = open(self.folder_path_best, 'a')
        train_log.write('best_score max_eval auc: %.4f acc: %.4f max_f1: %.4f max_test auc: %.4f acc: %.4f max_f1: %.4f \n'
                   % (self.max_eval_auc, self.max_eval_acc, self.max_eval_f1, self.max_test_auc, self.max_test_acc, self.max_test_f1))
        train_log.close()

        tr = 0
        
        if self.max_eval_auc > self.emb_score_auc_tmp[tr][self.hop][0]:
            self.emb_score_auc_tmp[tr][self.hop] = [self.max_eval_auc,self.max_test_auc]
            self.emb_score_acc_tmp[tr][self.hop] = [self.max_eval_acc,self.max_test_acc]
            self.emb_score_f1_tmp[tr][self.hop] = [self.max_eval_f1,self.max_test_f1]
            self.emb_score_recall_tmp[tr][self.hop] += [self.max_eval_recall,self.max_test_recall]
            self.sw_early_stop = 0
        else:
            self.sw_early_stop += 1


    def record_final_score(self):

        for i in range(len(self.emb_score_auc)):
            for j in range(len(self.emb_score_auc[i])):
                self.emb_score_auc[i][j] += self.emb_score_auc_tmp[i][j][1]
                self.emb_score_acc[i][j] += self.emb_score_acc_tmp[i][j][1]
                self.emb_score_f1[i][j] += self.emb_score_f1_tmp[i][j][1]
                self.emb_score_recall[i][j] += self.emb_score_recall_tmp[i][j][1]

        self.emb_score_auc_tmp = [[[0,0] for _ in range(5)]  for _ in range(4)]
        self.emb_score_acc_tmp = [[[0,0] for _ in range(5)]  for _ in range(4)]
        self.emb_score_f1_tmp = [[[0,0] for _ in range(5)]  for _ in range(4)]
        self.emb_score_recall_tmp = [[[0,0] for _ in range(5)]  for _ in range(4)]

        emb_score_auc = [0] * len(self.emb_score_auc)
        emb_score_acc = [0] * len(self.emb_score_acc)
        emb_score_f1 = [0] * len(self.emb_score_f1)
        emb_score_recall = [0] * len(self.emb_score_recall)

        for tr in range(len(self.emb_score_auc)):
            emb_score_auc[tr] = [round(i/self.counter, 6)  for i in self.emb_score_auc[tr]]
            emb_score_acc[tr] = [round(i/self.counter, 6)  for i in self.emb_score_acc[tr]]
            emb_score_f1[tr] = [round(i/self.counter, 6)  for i in self.emb_score_f1[tr]]
            emb_score_recall[tr] = [round(i/self.counter, 6)  for i in self.emb_score_recall[tr]]

        train_log = open(self.folder_path_best, 'a')
        train_log.write(f"no     auc = {emb_score_auc[0]}, acc = {emb_score_acc[0]}, f1 = {emb_score_f1[0]} \n")
        # train_log.write(f"no emb auc = {emb_score_auc[2]}, acc = {emb_score_acc[2]}, f1 = {emb_score_f1[2]} \n")
        train_log.write(f"{'*'*120} \n")
        train_log.close()

        self.sw_early_stop = 0

    def counter_add(self):
        self.counter += 1



class Train_info_record_emb_sw_ndcg:
    def __init__(self,args,tags):
        # cur_tim = time.strftime("%Y%m%d-%H%M%S")
        cur_tim = time.strftime("%Y%m%d")
        self.folder_path = f"{args.path.output}{str(cur_tim)}_{args.log_name}.log"
        self.folder_path_best = f"{args.path.output}{str(cur_tim)}_best_score_{args.log_name}.log"

        self.tags = tags
        self.tags_maxlen = max([len(t) for t in self.tags])

        self.emb_score_ndcg = [[0 for _ in range(5)]  for _ in range(len(tags))]
        self.emb_score_precision = [[0 for _ in range(5)]  for _ in range(len(tags))]
        self.emb_score_f1 = [[0 for _ in range(5)]  for _ in range(len(tags))]
        self.emb_score_recall = [[0 for _ in range(5)]  for _ in range(len(tags))]

        self.emb_score_ndcg_tmp = [[[0,0] for _ in range(5)]  for _ in range(len(tags))]
        self.emb_score_precision_tmp = [[[0,0] for _ in range(5)]  for _ in range(len(tags))]
        self.emb_score_f1_tmp = [[[0,0] for _ in range(5)]  for _ in range(len(tags))]
        self.emb_score_recall_tmp = [[[0,0] for _ in range(5)]  for _ in range(len(tags))]

        self.sw_early_stop = 0
        self.counter = 1

    def update_cur_train_info(self,args):    

        self.hop = args.n_iter

        self.ls_turn_up = args.ls_turn_up
        self.load_pretrain_emb = args.load_pretrain_emb


        self.max_train_auc = 0
        self.max_train_acc = 0
        self.max_train_f1 = 0
        self.max_eval_auc = 0
        self.max_eval_acc = 0
        self.max_eval_f1 = 0
        self.max_test_auc = 0
        self.max_test_acc = 0
        self.max_test_f1 = 0
        self.update_call = False

        self.max_eval_recall = [0 for i in range(5)]
        self.max_test_recall = [0 for i in range(5)]

        self.max_eval_ndcg = [0 for i in range(5)]
        self.max_test_ndcg = [0 for i in range(5)]

        self.max_eval_precision = [0 for i in range(5)]
        self.max_test_precision = [0 for i in range(5)]


        train_log = open(self.folder_path, 'a')
        train_log.write(f"lr = {args.lr}, hop = {args.n_iter}, np.epoch = {args.epoch}, neighbor_sample_size = {str(args.neighbor_sample_size)}\n")
        train_log.write(f"dataset = {args.dataset}, dim = {args.dim}, batch_size = {args.batch_size}, use_nb_rate = {args.use_neighbor_rate}, l2_weight = {args.l2_weight}, ls_weight = {args.ls_weight}, ls_true_up = {args.ls_turn_up} \n")
        cur_tim = time.strftime("%Y%m%d-%H%M%S")  
        train_log.write(f"pretrain_emb = {args.load_pretrain_emb}, tolerance = {args.tolerance}, early_decrease_lr = {args.early_decrease_lr}\n")
        train_log.close()
        train_log = open(self.folder_path_best, 'a')
        train_log.write(f"lr = {args.lr}, hop = {args.n_iter}, np.epoch = {args.epoch}, neighbor_sample_size = {str(args.neighbor_sample_size)}\n")
        train_log.write(f"dataset = {args.dataset}, dim = {args.dim}, batch_size = {args.batch_size}, use_nb_rate = {args.use_neighbor_rate}, l2_weight = {args.l2_weight}, ls_weight = {args.ls_weight}, ls_true_up = {args.ls_turn_up} \n")
        cur_tim = time.strftime("%Y%m%d-%H%M%S")
        train_log.write(f"pretrain_emb = {args.load_pretrain_emb}, tolerance = {args.tolerance}, early_decrease_lr = {args.early_decrease_lr}\n")
        train_log.close()

    def update_score(self, step, eval_score_info):
        train_ndcg, train_recall, train_precision = eval_score_info.train_ndcg_recall_pecision[0], eval_score_info.train_ndcg_recall_pecision[1], eval_score_info.train_ndcg_recall_pecision[2]
        eval_ndcg, eval_recall, eval_precision = eval_score_info.eval_ndcg_recall_pecision[0], eval_score_info.eval_ndcg_recall_pecision[1], eval_score_info.eval_ndcg_recall_pecision[2]
        test_ndcg, test_recall, test_precision =  eval_score_info.test_ndcg_recall_pecision[0], eval_score_info.test_ndcg_recall_pecision[1], eval_score_info.test_ndcg_recall_pecision[2]

        print(f"step = {step}, eval ndcg = {eval_ndcg} ")
        print(f"{step}, test ndcg = {test_ndcg} \n")
        print(f"step = {step}, eval recall = {eval_recall} ")
        print(f"{step}, test recall = {test_recall} \n")

        train_log = open(self.folder_path, 'a')
        train_log.write(f"step = {step}, eval ndcg = {eval_ndcg} ")
        train_log.write(f"{step}, test ndcg = {test_ndcg} \n")
        train_log.write(f"step = {step}, eval recall = {eval_recall} ")
        train_log.write(f"{step}, test recall = {test_recall} \n")
        train_log.close()

        if eval_recall[2] > self.max_eval_recall[2]:
            self.max_eval_ndcg =  eval_ndcg
            self.max_eval_recall = eval_recall
            self.max_eval_precision = eval_precision
            self.max_test_ndcg = test_ndcg
            self.max_test_recall = test_recall
            self.max_test_precision =  test_precision
            self.update_call = True
        else:
            self.update_call = False
        # train_log.close()
    def check_update_recall(self):
        return self.update_call

    def update_recall(self, step,  n_ndcg_eval, n_recall_eval, n_precision_eval, n_ndcg_test, n_recall_test, n_precision_test):

        train_log = open(self.folder_path, 'a')
        train_log.write(f"step = {step}, eval ndcg = {n_ndcg_eval} ")
        train_log.write(f"eval recall = {n_recall_eval} \n")
        train_log.write(f"step = {step}, test ndcg = {n_ndcg_test} ")
        train_log.write(f"test recall = {n_recall_test} \n")
        train_log.close()

    def train_over(self,tags_number):
        train_log = open(self.folder_path, 'a')
        train_log.write("*"*100)
        train_log.write("\n")

        print(f"best_score eval ndcg = {self.max_eval_ndcg}, eval recall = {self.max_eval_recall} \n")
        print(f"best_score test ndcg = {self.max_test_ndcg}, test recall = {self.max_test_recall} \n")

        train_log = open(self.folder_path_best, 'a')

        train_log.write(f"best_score eval ndcg = {self.max_eval_ndcg}, eval recall = {self.max_eval_recall} \n")
        train_log.write(f"best_score test ndcg = {self.max_test_ndcg}, test recall = {self.max_test_recall} \n")
        train_log.close()

        if self.load_pretrain_emb == False: tr = 0
        else: tr = 2

        if self.max_eval_recall[2] > self.emb_score_recall_tmp[tags_number][2][0]:
            for t_i in range(len(self.max_test_ndcg)):
                self.emb_score_ndcg_tmp[tags_number][t_i] = [self.max_eval_ndcg[t_i],self.max_test_ndcg[t_i]]
                self.emb_score_precision_tmp[tags_number][t_i] =  [self.max_eval_precision[t_i],self.max_test_precision[t_i]]
                self.emb_score_recall_tmp[tags_number][t_i] = [self.max_eval_recall[t_i],self.max_test_recall[t_i]] 
            self.sw_early_stop = 0
        else:
            self.sw_early_stop += 1

    def record_final_score(self):

        for i in range(len(self.emb_score_ndcg)):
            for j in range(len(self.emb_score_ndcg[i])):
                self.emb_score_ndcg[i][j] += self.emb_score_ndcg_tmp[i][j][1]
                self.emb_score_precision[i][j] += self.emb_score_precision_tmp[i][j][1]
                self.emb_score_recall[i][j] += self.emb_score_recall_tmp[i][j][1]

        self.emb_score_ndcg_tmp = [[[0,0] for _ in range(5)]  for _ in range(len(self.emb_score_recall))]
        self.emb_score_precision_tmp = [[[0,0] for _ in range(5)]  for _ in range(len(self.emb_score_recall))]
        self.emb_score_f1_tmp = [[[0,0] for _ in range(5)]  for _ in range(len(self.emb_score_recall))]
        self.emb_score_recall_tmp = [[[0,0] for _ in range(5)]  for _ in range(len(self.emb_score_recall))]

        emb_score_ndcg = [0.] * len(self.emb_score_ndcg)
        emb_score_precision = [0.] * len(self.emb_score_precision)
        emb_score_recall = [0.] * len(self.emb_score_recall)

        for tr in range(len(self.emb_score_ndcg)):
            emb_score_ndcg[tr] = [round(i/self.counter, 6)  for i in self.emb_score_ndcg[tr]]
            emb_score_precision[tr] = [round(i/self.counter, 6)  for i in self.emb_score_precision[tr]]
            emb_score_recall[tr] = [round(i/self.counter, 6)  for i in self.emb_score_recall[tr]]

        train_log = open(self.folder_path_best, 'a')
        for tags_label in range(len(self.tags)):
            space = ' '*(self.tags_maxlen - len(self.tags[tags_label]))
            train_log.write(f"{self.tags[tags_label]}{space} = {emb_score_ndcg[tags_label]}, recall = {emb_score_recall[tags_label]} \n")
        train_log.write(f"{'*'*120} \n")
        train_log.close()

        self.sw_early_stop = 0

    def counter_add(self):
        self.counter += 1


